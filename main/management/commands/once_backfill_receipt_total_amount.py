from django.core.management.base import BaseCommand
from django.db.models import Sum, F, ExpressionWrapper, BigIntegerField

from main.models import TradeReceipt

CHUNK_SIZE = 5000


class Command(BaseCommand):
    help = (
        'One-time backfill of TradeReceipt.total_amount for rows that predate the field. '
        'Processes in chunks of pks (not .iterator()) since the DB sits behind PgBouncer in '
        'transaction-pooling mode, which orphans server-side cursors held across connections.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report counts without writing any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        total_processed = 0

        while True:
            pks = list(
                TradeReceipt.objects.filter(total_amount__isnull=True)
                .order_by('pk').values_list('pk', flat=True)[:CHUNK_SIZE]
            )
            if not pks:
                break

            rows = (
                TradeReceipt.objects.filter(pk__in=pks)
                .annotate(computed_total=Sum(
                    ExpressionWrapper(F('items_trades__price') * F('items_trades__quantity'), output_field=BigIntegerField())
                ))
                .values('pk', 'computed_total')
            )

            if dry_run:
                # can't leave total_amount NULL and re-query the same "isnull" chunk forever,
                # so dry-run just reports on this one chunk and stops.
                total_processed = len(pks)
                break

            TradeReceipt.objects.bulk_update(
                [TradeReceipt(pk=row['pk'], total_amount=row['computed_total'] or 0) for row in rows],
                ['total_amount'],
                batch_size=CHUNK_SIZE,
            )
            total_processed += len(pks)
            self.stdout.write(f'Backfilled {total_processed} receipts...')

        if dry_run:
            self.stdout.write(f'Would backfill at least {total_processed} receipt(s) (showing first chunk only)')
        self.stdout.write(self.style.SUCCESS('Dry run complete, no changes made' if dry_run else f'Backfill complete: {total_processed} receipt(s) updated'))
