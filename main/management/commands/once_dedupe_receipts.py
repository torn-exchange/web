from collections import Counter
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count

from main.models import TradeReceipt


def trade_signature(receipt):
    """Multiset of (item_id, quantity) across a receipt's ItemTrade rows.

    A multiset (not a set) because a single trade paste can produce more
    than one ItemTrade row for the same item (parse_trade_text doesn't
    merge duplicate item names unless trade_enable_sets is on), so two
    receipts are only "identical" if they have the same rows, not just
    the same set of item ids.
    """
    return frozenset(
        Counter((it.item_id, it.quantity) for it in receipt.items_trades.all()).items()
    )


class Command(BaseCommand):
    help = (
        'One-time cleanup for duplicate TradeReceipts caused by the browser '
        'extension being resubmitted after an accidental close (the legacy '
        'create_receipt endpoint has no trade_id-based idempotency). '
        'Duplicates are receipts with the same owner, same seller, an '
        'identical multiset of (item, quantity) across their ItemTrades, '
        'and created_at within 2 minutes of each other. The earliest '
        'receipt in each such cluster is kept; the rest are deleted. '
        'Processes one (owner, seller) group at a time rather than loading '
        'the whole table into memory, since TradeReceipt/ItemTrade can run '
        'into the millions of rows in production.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be removed without deleting anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Cheap, DB-side aggregation to find only the (owner, seller) pairs that
        # could possibly contain a duplicate -- the vast majority of pairs have
        # exactly one receipt and can be skipped without ever being loaded.
        # Materialized as a plain list (not .iterator()): these rows are just
        # (owner_id, seller, count) tuples, tiny compared to the actual
        # TradeReceipt/ItemTrade data that motivated avoiding a single big
        # query in the first place. .iterator() opens a server-side cursor
        # pinned to one physical connection, which breaks in production here
        # since the DB sits behind PgBouncer in transaction-pooling mode --
        # each of the per-group queries inside this loop can get handed a
        # different pooled connection, orphaning that cursor ("cursor ...
        # does not exist").
        candidate_groups = list(
            TradeReceipt.objects.order_by()
            .values('owner_id', 'seller')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        clusters_found = 0
        receipts_removed = 0
        groups_scanned = 0

        for group in candidate_groups:
            groups_scanned += 1
            receipts = list(
                TradeReceipt.objects.filter(
                    owner_id=group['owner_id'], seller=group['seller']
                )
                .prefetch_related('items_trades')
                .order_by('created_at')
            )

            # Clustering is done first, in full, using each receipt's original id --
            # deleting a receipt sets its .id to None, so deletions must not happen
            # until after this group has finished being scanned for clusters.
            used_ids = set()
            group_clusters = []
            for i, first in enumerate(receipts):
                if first.id in used_ids:
                    continue
                first_signature = trade_signature(first)
                cluster = [first]
                for other in receipts[i + 1:]:
                    if other.id in used_ids:
                        continue
                    if other.created_at - first.created_at > timedelta(minutes=2):
                        # receipts is sorted by created_at, so no later receipt
                        # can be within the window either
                        break
                    if trade_signature(other) == first_signature:
                        cluster.append(other)
                        used_ids.add(other.id)

                if len(cluster) > 1:
                    group_clusters.append(cluster)

            for cluster in group_clusters:
                clusters_found += 1
                canonical, duplicates = cluster[0], cluster[1:]
                self.stdout.write(
                    f'Keeping TradeReceipt(id={canonical.id}, created_at={canonical.created_at}) as canonical; '
                    f'{"would remove" if dry_run else "removing"} {len(duplicates)} duplicate(s): '
                    f'{[dup.id for dup in duplicates]}'
                )
                for dup in duplicates:
                    if not dry_run:
                        dup.items_trades.all().delete()
                        dup.delete()
                    receipts_removed += 1

            if groups_scanned % 5000 == 0:
                self.stdout.write(f'... scanned {groups_scanned} candidate groups so far')

        self.stdout.write(self.style.SUCCESS(
            f'Scanned {groups_scanned} candidate (owner, seller) group(s); '
            f'{"would remove" if dry_run else "removed"} {receipts_removed} duplicate receipt(s) '
            f'across {clusters_found} cluster(s)'
        ))
