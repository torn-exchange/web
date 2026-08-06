from django.core.management.base import BaseCommand
from django.db.models import Count

from main.models import Item, Listing, ItemTrade, ItemVariation


class Command(BaseCommand):
    help = (
        'One-time cleanup for Item rows that share the same non-null item_id '
        '(caused by update_items2/update_items_async keying their upsert on '
        'name instead of item_id, so a Torn-side rename created a phantom '
        'duplicate row instead of updating the existing one). For each '
        'item_id with duplicates, keeps the most-recently-updated row as '
        'canonical, reassigns Listing/ItemTrade/ItemVariation rows pointing '
        'at the older duplicates to the canonical row (resolving the '
        'Listing unique_together=(owner, item) collision by keeping '
        'whichever of the two colliding Listings was more recently '
        'updated), then deletes the now-orphaned duplicate Item rows. '
        'Must be run (without --dry-run) before the unique_non_null_item_id '
        'DB constraint is applied, or that migration will fail against '
        'any remaining duplicates.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        duplicated_item_ids = (
            Item.objects.exclude(item_id__isnull=True)
            .values('item_id')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
            .values_list('item_id', flat=True)
        )

        groups_found = 0
        rows_removed = 0
        collisions_resolved = 0

        for item_id in duplicated_item_ids:
            groups_found += 1
            rows = list(Item.objects.filter(item_id=item_id).order_by('-last_updated'))
            canonical, duplicates = rows[0], rows[1:]

            self.stdout.write(
                f'item_id={item_id}: canonical=Item(id={canonical.id}, name="{canonical.name}", '
                f'last_updated={canonical.last_updated}), {len(duplicates)} duplicate(s)'
            )

            for dup in duplicates:
                moved_trades = ItemTrade.objects.filter(item=dup).count()
                moved_variations = ItemVariation.objects.filter(item=dup).count()
                if not dry_run:
                    ItemTrade.objects.filter(item=dup).update(item=canonical)
                    ItemVariation.objects.filter(item=dup).update(item=canonical)
                self.stdout.write(
                    f'  {"Would move" if dry_run else "Moved"} {moved_trades} ItemTrade(s) and '
                    f'{moved_variations} ItemVariation(s) from Item(id={dup.id}) to canonical'
                )

                for listing in Listing.objects.filter(item=dup):
                    colliding = Listing.objects.filter(owner=listing.owner, item=canonical).first()
                    if colliding is not None:
                        collisions_resolved += 1
                        if listing.last_updated >= colliding.last_updated:
                            self.stdout.write(
                                f'  Collision for owner={listing.owner_id}: keeping Listing(id={listing.id}, '
                                f'last_updated={listing.last_updated}) repointed to canonical, dropping '
                                f'Listing(id={colliding.id}, last_updated={colliding.last_updated})'
                            )
                            if not dry_run:
                                colliding.delete()
                                listing.item = canonical
                                listing.save(update_fields=['item'])
                        else:
                            self.stdout.write(
                                f'  Collision for owner={listing.owner_id}: keeping Listing(id={colliding.id}, '
                                f'last_updated={colliding.last_updated}) on canonical, dropping '
                                f'Listing(id={listing.id}, last_updated={listing.last_updated})'
                            )
                            if not dry_run:
                                listing.delete()
                    else:
                        self.stdout.write(
                            f'  {"Would repoint" if dry_run else "Repointed"} Listing(id={listing.id}, '
                            f'owner={listing.owner_id}) to canonical'
                        )
                        if not dry_run:
                            listing.item = canonical
                            listing.save(update_fields=['item'])

                if not dry_run:
                    dup.delete()
                rows_removed += 1

        self.stdout.write(self.style.SUCCESS(
            f'{"Would remove" if dry_run else "Removed"} {rows_removed} duplicate Item row(s) '
            f'across {groups_found} item_id group(s); {collisions_resolved} Listing collision(s) '
            f'{"would be" if dry_run else "were"} resolved'
        ))
