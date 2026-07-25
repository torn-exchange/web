from django.core.management.base import BaseCommand
from django.db.models import Q
from users.models import Profile
from main.models import Listing


class Command(BaseCommand):
    help = (
        'One-time backfill for the hidden_by_category/hidden_by_inactivity/hidden_by_vacation '
        'split. Attributes existing hidden=True listings to hidden_by_category where the owner '
        'has that category in hidden_categories. Any hidden=True listing left with no reason '
        'flag afterwards is unhidden, since hidden_by_inactivity/hidden_by_vacation cannot be '
        'inferred retroactively and hidden with no traceable reason is not a state we want to keep.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report counts without writing any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        profiles_with_hidden_cats = list(Profile.objects.exclude(hidden_categories={}))
        category_matches = 0

        for profile in profiles_with_hidden_cats:
            hidden_cats = [cat for cat, is_hidden in profile.hidden_categories.items() if is_hidden]
            if not hidden_cats:
                continue

            qs = Listing.objects.filter(
                owner=profile, hidden=True, hidden_by_category=False, item__item_type__in=hidden_cats
            )
            count = qs.count()
            if count and not dry_run:
                qs.update(hidden_by_category=True)
            category_matches += count

        self.stdout.write(f'{"Would newly attribute" if dry_run else "Newly attributed"} hidden_by_category on {category_matches} listings')

        no_reason = Q(hidden_by_category=False, hidden_by_inactivity=False, hidden_by_vacation=False)
        unexplained = Listing.objects.filter(hidden=True).filter(no_reason)
        # in dry-run, category_matches above weren't actually written, so re-derive
        # what "unexplained" would look like post-backfill for an accurate report
        if dry_run:
            matched_pks = set()
            for profile in profiles_with_hidden_cats:
                hidden_cats = [cat for cat, is_hidden in profile.hidden_categories.items() if is_hidden]
                if not hidden_cats:
                    continue
                matched_pks.update(
                    Listing.objects.filter(
                        owner=profile, hidden=True, hidden_by_category=False, item__item_type__in=hidden_cats
                    ).values_list('pk', flat=True)
                )
            unexplained = unexplained.exclude(pk__in=matched_pks)

        unexplained_count = unexplained.count()
        self.stdout.write(f'{"Would unhide" if dry_run else "Unhiding"} {unexplained_count} listings with no discoverable hide reason')
        if not dry_run:
            unexplained.update(hidden=False)

        self.stdout.write(self.style.SUCCESS('Dry run complete, no changes made' if dry_run else 'Backfill complete'))
