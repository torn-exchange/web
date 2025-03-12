from django.core.management.base import BaseCommand
from main.models import ItemBonus, ItemVariation


class Command(BaseCommand):
    help = 'Populates ItemBonus table with predefined bonus titles'

    def handle(self, *args, **options):
        item_variations = ItemVariation.objects.all()

        for item_variation in item_variations:
            market_type = 'bazaar'
            if item_variation.owner_id == None or item_variation.owner_id == 0 or item_variation.owner_id == '':
                market_type = 'item market'

            item_variation.market_type = market_type
            item_variation.save()
            print(f'Updated {item_variation.id} with market type {market_type}')
