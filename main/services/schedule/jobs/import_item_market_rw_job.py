from time import sleep
from main.models import ItemVariation, ItemVariationBonuses, Item, ItemBonus, Job
from main.services.api.torn.items.torn_item_market_api_service import TornItemMarketAPIService
from main.services.schedule.jobs.abstract_job import AbstractJob
from datetime import datetime
from django.utils import timezone


class ImportItemMarketRW(AbstractJob):
    api_item_data = []

    def __init__(self):
        naive_datetime = datetime.now()
        aware_datetime = timezone.make_aware(naive_datetime)
        self.last_sync_at = aware_datetime

    def handle(self, job: Job, payload: dict):
        self.job = job
        print('TestJob running with payload:', payload)
        super().log('Started')

        updated_items = 0
        items = self.get_items()

        for item in items:
            self.api_item_data = []

            self.get_rw_listings(item.item_id)

            sleep(2)

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

                    updated_items += 1

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

        super().log('Complete', {'items': updated_items})
        super().resolve(True)

    def get_items(self):
        return Item.objects.filter(item_type__in=['Melee', 'Primary', 'Secondary'])

    def get_rw_listings(self, item_id, offset = 0):
        service = TornItemMarketAPIService()
        response = service.get_rw_items(item_id, offset)

        if not response['success']:
            if 'error' in response['data']:
                print(response['data']['error'])

                if response['data']['error']['code'] == 5 or response['data']['error']['code'] == 8:
                    sleep(2)
                    self.get_rw_listings(item_id, offset)
                return

        response = response['data']

        if 'itemmarket' not in response:
            return

        if 'listings' not in response['itemmarket']:
            return

        if '_metadata' not in response:
            return

        self.api_item_data.append(response['itemmarket']['listings'])

        nextPage = response['_metadata']['next']
        if nextPage is not None:
            length = len(response['itemmarket']['listings'])
            if length == 100:
                self.get_rw_listings(item_id, offset + 100)

    def map_item(self, item_data, item):
        bonuses = []
        for bonus in item_data['itemDetails']['bonuses']:
            db_bonus = ItemBonus.objects.filter(title=bonus['title']).first()

            bonuses.append({
                'value': bonus['value'],
                'type': 'tick' if 'Disarm' in db_bonus.title else 'percentage',
                'description': bonus['description'],
                'bonus_id': db_bonus.id
            })

        return {
            'item_id': item.item_id,
            'uid': item_data['itemDetails']['uid'],
            'price': item_data['price'],
            'accuracy': item_data['itemDetails']['stats']['accuracy'],
            'damage': item_data['itemDetails']['stats']['damage'],
            'quality': item_data['itemDetails']['stats']['quality'],
            'rarity': item_data['itemDetails']['rarity'],
            'bonuses': bonuses
        }