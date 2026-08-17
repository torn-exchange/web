import concurrent.futures
import os
import random
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

from django.conf import settings as project_settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import Item
from main.management.commands.update_items2 import (
    Command as LegacyUpdateItemsCommand,
    create_or_update_sets,
    get_lowest_market_price,
    recalculate_listings_for_item,
    sanitize_numbers,
)
from main.services.api.weav3r.marketplace_api_service import Weav3rMarketplaceApiService
from users.models import Profile

# With a pool of thousands of API keys, per-key throttling is essentially a
# non-issue (each key gets used a fraction of a time per run) - the real
# ceiling is Torn's per-IP limit, which we don't have a hard number for yet,
# so this is deliberately generous rather than a tight guess. Tune down if
# "Too many requests" errors show up in practice.
MAX_THREADS = 40
MAX_CALLS_PER_MINUTE = 3000
MAX_RETRIES_PER_ITEM = 3

# The Torn API fetch is network-bound and benefits from MAX_THREADS-way
# parallelism, but recalculate_listings_for_item() issues one DB query per
# Listing (N+1) and 40 threads doing that simultaneously exhausts the
# PgBouncer connection pool, turning cheap writes into long queue waits
# (measured: ~0.2s of real write work stretching to ~44s average under full
# concurrency). Capping concurrent DB-write sections separately from the
# API-fetch concurrency keeps the pool from being overwhelmed.
MAX_CONCURRENT_DB_WRITERS = 8


def _load_api_keys():
    """Fetch all usable API keys ONCE as a plain list.

    update_items2.get_random_key() builds a brand-new
    Profile.objects.exclude(...) queryset on every call, so calling it once
    per item (1000+ times) forces Django to re-fetch and materialize the
    entire keyed-profile table from the DB that many times, serially, before
    any request work even starts - this was the actual dominant cost, not
    the Torn API calls themselves. Fetching once into a plain list makes
    random.choice() an in-memory operation, safe to call from any thread.
    """
    keys = list(
        Profile.objects.exclude(api_key=None).exclude(api_key='')
        .values_list('api_key', flat=True)
    )
    return keys or [os.getenv('SYSTEM_API_KEY')]


class _SharedRateLimiter:
    """Paces requests across worker threads and coordinates rate-limit backoff.

    Without this, each thread would sleep independently on a "Too many
    requests" response (as the abandoned update_items_async.py experiment
    did), which doesn't reduce the aggregate request rate and can make
    repeated rate-limiting worse.
    """

    def __init__(self, max_calls_per_minute=MAX_CALLS_PER_MINUTE):
        self._lock = threading.Lock()
        self._call_times = []
        self._max_calls = max_calls_per_minute
        self._blocked_until = 0.0

    def wait_for_slot(self):
        while True:
            with self._lock:
                now = time.monotonic()
                if now < self._blocked_until:
                    sleep_for = self._blocked_until - now
                else:
                    self._call_times = [t for t in self._call_times if now - t < 60]
                    if len(self._call_times) < self._max_calls:
                        self._call_times.append(now)
                        return
                    sleep_for = 60 - (now - self._call_times[0])
            time.sleep(max(sleep_for, 0.05))

    def report_rate_limited(self, backoff_seconds=30):
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.monotonic() + backoff_seconds)


class _Benchmark:
    """TEMPORARY instrumentation for comparing runtime against update_items2.

    Not meant to be committed - strip before merging.
    """

    # A single get_lowest_market_price() call taking this long almost
    # certainly means it hit Torn's real rate limit and ran the internal
    # time.sleep(30) branch, rather than just normal network latency.
    SLOW_CALL_THRESHOLD_SECONDS = 5

    def __init__(self, total):
        self._lock = threading.Lock()
        self._total = total
        self._completed = 0
        self._seen_threads = set()
        self._item_durations = []
        self._call_durations = []
        self._likely_rate_limited_calls = 0
        self._db_phase_durations = defaultdict(list)
        self.start_perf = time.perf_counter()
        self.start_wall = datetime.now()

    def note_api_call(self, duration):
        with self._lock:
            self._call_durations.append(duration)
            if duration > self.SLOW_CALL_THRESHOLD_SECONDS:
                self._likely_rate_limited_calls += 1

    def note_db_phase(self, phase, duration):
        with self._lock:
            self._db_phase_durations[phase].append(duration)

    def note_thread_start(self):
        name = threading.current_thread().name
        with self._lock:
            if name not in self._seen_threads:
                self._seen_threads.add(name)
                print(f'[bench] thread spawned/first-used: {name} '
                      f'(active threads so far: {len(self._seen_threads)})')

    def note_item_done(self, item_id, duration):
        with self._lock:
            self._completed += 1
            self._item_durations.append(duration)
            elapsed = time.perf_counter() - self.start_perf
            print(f'[bench] {self._completed}/{self._total} done '
                  f'(item {item_id} took {duration:.2f}s on {threading.current_thread().name}, '
                  f'elapsed {elapsed:.1f}s)')

    def summary(self):
        end_perf = time.perf_counter()
        end_wall = datetime.now()
        duration = end_perf - self.start_perf
        avg = (sum(self._item_durations) / len(self._item_durations)) if self._item_durations else 0
        print('[bench] ===== summary =====')
        print(f'[bench] start: {self.start_wall.isoformat()}')
        print(f'[bench] end:   {end_wall.isoformat()}')
        print(f'[bench] total duration: {duration:.2f}s')
        print(f'[bench] items processed: {self._completed}/{self._total}')
        print(f'[bench] avg per-item request time: {avg:.3f}s')
        print(f'[bench] distinct worker threads used: {len(self._seen_threads)} {sorted(self._seen_threads)}')
        total_calls = len(self._call_durations)
        avg_call = (sum(self._call_durations) / total_calls) if total_calls else 0
        pct_slow = (self._likely_rate_limited_calls / total_calls * 100) if total_calls else 0
        print(f'[bench] individual API calls: {total_calls}, avg {avg_call:.2f}s')
        print(f'[bench] calls that look rate-limited (> {self.SLOW_CALL_THRESHOLD_SECONDS}s, '
              f'likely hit internal 30s sleep): {self._likely_rate_limited_calls}/{total_calls} '
              f'({pct_slow:.1f}%)')
        print('[bench] --- DB write path ---')
        total_db_time = 0.0
        for phase in sorted(self._db_phase_durations):
            durations = self._db_phase_durations[phase]
            phase_total = sum(durations)
            total_db_time += phase_total
            print(f'[bench]   {phase}: n={len(durations)}, total={phase_total:.2f}s, '
                  f'avg={phase_total / len(durations):.3f}s, max={max(durations):.2f}s')
        print(f'[bench]   TOTAL db time summed across all threads: {total_db_time:.2f}s '
              f'(wall-clock duration was {duration:.2f}s, {MAX_THREADS} threads)')
        print('[bench] ====================')


@contextmanager
def _timed(benchmark, phase):
    start = time.perf_counter()
    yield
    if benchmark is not None:
        benchmark.note_db_phase(phase, time.perf_counter() - start)


def _process_item_row(row, api_key, bazaar_by_item_id, rate_limiter, api_keys, db_write_gate, benchmark=None):
    item_id = row['image'].replace(
        'https://www.torn.com/images/items/', '').replace('/large.png', '')
    bazaar_average = bazaar_by_item_id.get(int(item_id))

    if benchmark is not None:
        benchmark.note_thread_start()
    item_start = time.perf_counter()

    def _call(key):
        call_start = time.perf_counter()
        result = get_lowest_market_price(item_id, key, row['market_value'], bazaar_average)
        if benchmark is not None:
            benchmark.note_api_call(time.perf_counter() - call_start)
        return result

    rate_limiter.wait_for_slot()
    TE_price = _call(api_key)
    retries = 0
    while bool(TE_price) is not True and retries < MAX_RETRIES_PER_ITEM:
        # get_lowest_market_price already sleeps 30s internally on a genuine
        # "too many requests" hit, so it doesn't need extra global backoff
        # layered on top here - that was compounding into an effectively
        # permanent stall whenever a stale/bad key kept erroring out. Instead:
        # bound the retries and swap to a fresh key each time, in case the
        # error was key-specific rather than a real rate limit.
        retries += 1
        print(f"Repeating request for item: {item_id} (retry {retries}/{MAX_RETRIES_PER_ITEM})")
        api_key = random.choice(api_keys)
        rate_limiter.wait_for_slot()
        TE_price = _call(api_key)
        if TE_price == 0:
            break

    if benchmark is not None:
        benchmark.note_item_done(item_id, time.perf_counter() - item_start)

    if TE_price is None:
        # Every attempt errored out (rate limit, bad key, network hiccup) --
        # leave the existing TE_value alone rather than writing a price. Left
        # unguarded, sanitize_numbers(None) below coerces this into 0, which
        # then gets propagated to every trader's listings for this item via
        # recalculate_listings_for_item, wiping out real prices until the
        # next hourly run happens to succeed.
        print(f'Skipping update for {row["name"]} [{item_id}]: no valid price after '
              f'{MAX_RETRIES_PER_ITEM} retries')
        return

    # DB writes (esp. recalculate_listings_for_item's N+1 per-listing saves)
    # get throttled to MAX_CONCURRENT_DB_WRITERS at a time, decoupled from
    # MAX_THREADS, so 40-way API-fetch parallelism doesn't translate into
    # 40-way contention on the Postgres/PgBouncer connection pool.
    with db_write_gate:
        # item_id (Torn's stable identifier) is the true identity here, not
        # name -- a Torn-side rename must update this row in place rather
        # than create a phantom duplicate, so look up (and later upsert) by
        # item_id.
        with _timed(benchmark, 'db_lookup'):
            item_in_our_db = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()

        if item_in_our_db is not None:
            if TE_price == 0 and item_in_our_db.TE_value:
                # A fetch that comes back with a genuine "no price data
                # anywhere" 0 is far more likely a bad/incomplete read than a
                # real crash to literal $0 -- don't let it clobber a known
                # good price. Leaves TE_value untouched; a later run with
                # good data will update it normally.
                print(f'Skipping update for {row["name"]} [{item_id}]: fetched price is 0 '
                      f'but existing TE_value is {item_in_our_db.TE_value}')
            elif item_in_our_db.TE_value != TE_price:
                try:
                    for key in ['buy_price', 'sell_price', 'market_value']:
                        row[key] = sanitize_numbers(row[key])
                    TE_price = sanitize_numbers(TE_price)

                    with _timed(benchmark, 'db_upsert_existing'):
                        item_obj, _ = Item.objects.update_or_create(
                            item_id=item_id,
                            defaults=dict(
                                name=row['name'],
                                description=row['description'],
                                requirement=row['requirement'],
                                item_type=row['type'],
                                weapon_type=row['weapon_type'],
                                buy_price=row['buy_price'],
                                sell_price=row['sell_price'],
                                market_value=row['market_value'],
                                circulation=row['circulation'],
                                image_url=row['image'],
                                TE_value=TE_price,
                                bazaar_average=bazaar_average,
                                bazaar_fetched_at=timezone.now() if bazaar_average else None,
                            ),
                        )
                    with _timed(benchmark, 'db_recalculate_listings'):
                        recalculate_listings_for_item(item_obj)
                    # print(
                    #     f'Updated {row["name"]} [{item_id}] market price to {row["market_value"]} and TE_price to {TE_price}')
                except Exception as e:
                    print(e)
                    print(f'Did NOT save item: {row["name"]} [{item_id}]', row)
            else:
                print(f'No update needed for {row["name"]} [{item_id}]')
        else:
            try:
                for key in ['buy_price', 'sell_price', 'market_value']:
                    row[key] = sanitize_numbers(row[key])
                TE_price = sanitize_numbers(TE_price)

                with _timed(benchmark, 'db_upsert_new'):
                    Item.objects.update_or_create(
                        item_id=item_id,
                        defaults=dict(
                            name=row['name'],
                            description=row['description'],
                            requirement=row['requirement'],
                            item_type=row['type'],
                            weapon_type=row['weapon_type'],
                            buy_price=row['buy_price'],
                            sell_price=row['sell_price'],
                            market_value=row['market_value'],
                            circulation=row['circulation'],
                            image_url=row['image'],
                            TE_value=TE_price,
                            bazaar_average=bazaar_average,
                            bazaar_fetched_at=timezone.now() if bazaar_average else None,
                        ),
                    )
                print(f'Created {row["name"]} -{item_id} as a new entry on the db')
            except Exception as e:
                print(e)
                print(f'Did NOT save item: {row["name"]} [{item_id}]', row)


def _populate(df):
    print('Updating items (fast)...')
    create_or_update_sets()

    # Fetched once per run (not once per item) so a slow/rate-limited weav3r
    # response doesn't multiply the command's runtime.
    bazaar_by_item_id = Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id()

    qualifying_rows = [
        row for _, row in df.iterrows()
        if row['circulation'] >= project_settings.MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM
    ]

    api_keys = _load_api_keys()
    print(f'[bench] loaded {len(api_keys)} usable API keys')

    rate_limiter = _SharedRateLimiter()
    db_write_gate = threading.Semaphore(MAX_CONCURRENT_DB_WRITERS)
    benchmark = _Benchmark(total=len(qualifying_rows))
    print(f'[bench] dispatching {len(qualifying_rows)} items across {MAX_THREADS} threads, '
          f'started at {benchmark.start_wall.isoformat()}')

    # Not using `with ThreadPoolExecutor() as executor:` on purpose: its
    # __exit__ always does shutdown(wait=True), which blocks until every
    # already-submitted future finishes - so Ctrl+C looks "stuck" until the
    # entire backlog drains. The try/except below wraps dispatch itself too
    # (not just as_completed), since KeyboardInterrupt can land while futures
    # are still being submitted.
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_THREADS, thread_name_prefix='update-items-fast')
    try:
        futures = [
            executor.submit(_process_item_row, row, random.choice(api_keys),
                             bazaar_by_item_id, rate_limiter, api_keys, db_write_gate, benchmark)
            for row in qualifying_rows
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print("update_items_fast ERROR", e)
    except KeyboardInterrupt:
        print('\n[bench] KeyboardInterrupt: stopping. Worker threads are '
              'non-daemon and may be blocked inside a network call Python '
              'cannot interrupt, so this process is being force-terminated '
              'now rather than waiting for them to drain naturally.')
        benchmark.summary()
        # os._exit (not sys.exit) skips normal interpreter/thread-join
        # shutdown, which is exactly what's needed here: a plain exit()
        # would still block waiting for the executor's non-daemon threads.
        os._exit(1)

    executor.shutdown(wait=True)
    benchmark.summary()
    print('Done!')


class Command(BaseCommand):
    help = (
        'Faster, thread-parallelized replacement for update_items2 that '
        'fetches Torn itemmarket prices concurrently instead of sequentially, '
        'while honoring Torn\'s rate limit via a shared limiter.'
    )

    def add_arguments(self, parser):
        parser.add_argument('item_name', nargs='?', type=str)

    def handle(self, *args, **options):
        df = LegacyUpdateItemsCommand.df
        if options['item_name']:
            df = df[df['name'] == options['item_name']]
            # print(df.to_string())
        _populate(df)
