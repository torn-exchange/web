import time

from django.core.management.base import BaseCommand
from time import sleep
from datetime import datetime

from django.utils import timezone

from main.models import Item, ItemVariation, ItemBonus, ItemVariationBonuses
from main.services.api.torn.items.torn_item_market_api_service import TornItemMarketAPIService


class Command(BaseCommand):
    help = 'Grab RWs from Item Market'
    api_item_data = []

    def __init__(self):
        naive_datetime = datetime.now()
        aware_datetime = timezone.make_aware(naive_datetime)
        self.last_sync_at = aware_datetime
        super().__init__()

    def get_items(self):
        return Item.objects.filter(item_type__in=['Melee', 'Primary', 'Secondary'])

    def get_rw_listings(self, item_id, offset = 0):
        service = TornItemMarketAPIService()
        response = service.get_rw_items(item_id, offset)

        if not response['success']:
            if 'error' in response['data']:
                print(response['data']['error'])

                if response['data']['error']['code'] == 5 or response['data']['error']['code'] == 8:
                    time.sleep(2)
                    self.get_rw_listings(item_id, offset)
                return

        response = response['data']

        if 'itemmarket' not in response:
            print(response)
            return

        if 'listings' not in response['itemmarket']:
            print(response)
            return

        if '_metadata' not in response:
            print(response)
            return

        self.api_item_data.append(response['itemmarket']['listings'])

        nextPage = response['_metadata']['next']
        if nextPage is None:
            print("No more pages")
        else:
            length = len(response['itemmarket']['listings'])
            if length == 100:
                self.get_rw_listings(item_id, offset + 100)

    def map_item(self, item_data, item):
        bonuses = []
        for bonus in item_data['item_details']['bonuses']:
            print(bonus)
            db_bonus = ItemBonus.objects.filter(title=bonus['title']).first()

            bonuses.append({
                'value': bonus['value'],
                'type': 'tick' if 'Disarm' in db_bonus.title else 'percentage',
                'description': bonus['description'],
                'bonus_id': db_bonus.id
            })

        return {
            'item_id': item.item_id,
            'uid': item_data['item_details']['uid'],
            'price': item_data['price'],
            'accuracy': item_data['item_details']['stats']['accuracy'],
            'damage': item_data['item_details']['stats']['damage'],
            'quality': item_data['item_details']['stats']['quality'],
            'rarity': item_data['item_details']['rarity'],
            'bonuses': bonuses
        }

    def handle(self, *args, **options):
        items = self.get_items()

        for item in items:
            self.api_item_data = []

            print(f"Getting RWs for: {item.name} - id: {item.item_id}")
            self.get_rw_listings(item.item_id)

            print(f"Total RWs for: {item.name} - id: {item.item_id}: {sum(len(batch) for batch in self.api_item_data)}")
            sleep(2)

            print(f"Saving RWs for: {item.name} - id: {item.item_id}")

            for set in self.api_item_data:
                for item_data in set:
                    item_normalized = self.map_item(item_data, item)

                    if item_normalized['rarity'] == '' or item_normalized['rarity'] is None:
                        continue

                    item_variation, created = ItemVariation.objects.update_or_create(
                        uid=item_normalized['uid'],
                        item_id=item.id,
                        defaults={
                            "market_type": "item market",
                            "accuracy": item_normalized['accuracy'],
                            "damage": item_normalized['damage'],
                            "quality": item_normalized['quality'],
                            "price": item_normalized['price'],
                            "rarity": item_normalized['rarity'].capitalize(),
                            "last_sync_at": self.last_sync_at,
                            "is_saleable": True,
                        }
                    )

                    item_variation.refresh_from_db()

                    for bonus in item_normalized['bonuses']:
                        ItemVariationBonuses.objects.update_or_create(
                            bonus_id=bonus['bonus_id'],
                            item_variation_id=item_variation.id,
                            defaults={
                                "value": bonus['value'],
                                "description": bonus['description'],
                                "type": bonus['type']
                            }
                        )
