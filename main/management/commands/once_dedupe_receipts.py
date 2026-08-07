from collections import Counter, defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand

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
        'receipt in each such cluster is kept; the rest are deleted.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be removed without deleting anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        groups = defaultdict(list)
        for receipt in (
            TradeReceipt.objects.select_related('owner')
            .prefetch_related('items_trades')
            .order_by('created_at')
        ):
            groups[(receipt.owner_id, receipt.seller)].append(receipt)

        # Clustering is done first, in full, using each receipt's original id --
        # deleting a receipt sets its .id to None, so deletions must not happen
        # until after every group has finished being scanned for clusters.
        clusters = []
        for receipts in groups.values():
            used_ids = set()
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
                    clusters.append(cluster)

        clusters_found = len(clusters)
        receipts_removed = 0
        for cluster in clusters:
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

        self.stdout.write(self.style.SUCCESS(
            f'{"Would remove" if dry_run else "Removed"} {receipts_removed} duplicate receipt(s) '
            f'across {clusters_found} cluster(s)'
        ))
