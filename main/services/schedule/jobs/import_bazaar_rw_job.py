import time
import traceback

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json
import os
from time import sleep
from datetime import datetime
from main.models import Item, ItemVariation, ItemBonus, ItemVariationBonuses
from main.services.api.torn.player.torn_player_api_service import TornPlayerAPIService
from users.models import Profile
from time import sleep
from main.models import ItemVariation, ItemVariationBonuses, Item, ItemBonus, Job
from main.services.api.torn.items.torn_item_market_api_service import TornItemMarketAPIService
from main.services.schedule.jobs.abstract_job import AbstractJob
from datetime import datetime
from django.utils import timezone


class ImportBazaarRW(AbstractJob):
    api_item_data = []

    def __init__(self):
        naive_datetime = datetime.now()
        aware_datetime = timezone.make_aware(naive_datetime)
        self.last_sync_at = aware_datetime
        self.api_key = os.getenv('SYSTEM_API_KEY')
        self.rare_items = []
        self.db_items = []
        self.max_workers = 5  # Adjust based on API rate limits
        self.timeout = 10  # seconds
        self.bonuses = ItemBonus.objects.all()
        self.items = Item.objects.all()
        self.special_key = os.getenv('SPECIAL_KEY')

    def handle(self, job: Job, payload: dict):
        self.job = job
        print('TestJob running with payload:', payload)
        super().log('Started')

        # Get items from TornPal API
        status = self.get_item_details()
        print("STATUS", status)

        # print(json.dumps(self.rare_items, indent=2))

        # After collecting items, save to database
        if self.rare_items:
            self.save_to_database()
        else:
            print('No rare items to save')

        # Final summary
        print(
                f'\nProcess completed:\n'
                # f'Total items processed: {len(item_ids)}\n'
                # f'Successful: {successful}\n'
                # f'Failed: {failed}\n'
                f'Rare items found: {len(self.rare_items)}'
        )

    def ensure_user(self, player_id):
        profile = Profile.objects.filter(torn_id=player_id).first()
        if not profile:
            try:
                service = TornPlayerAPIService()
                response = service.get_profile(player_id)

                if 'error' in response['data']:
                    error = response['data']['error']
                    print(f'Data error: {error}')
                    return None

                user = User.objects.create_user(player_id, 'johnpassword')
                user.save()
                user.refresh_from_db()
                user.profile.torn_id = player_id
                user.profile.name = response['data']['name']
                user.save()
                user.refresh_from_db()

                profile = user.profile
            except Exception as e:
                print("Error occurred:", e)
                print("Detailed traceback:")
                traceback.print_exc()
                return None

        time.sleep(5)
        return profile

    def map_item_id(self, item):
        database_item = self.items.filter(item_id=item['item_id']).first()
        if not database_item:
            return None

        item['item_id'] = database_item.id
        return item

    def get_item_details(self):
        """Fetch item details from TornPal API"""
        url = f'https://tornpal.com/api/v1/markets/rwsearch?specialkey={self.special_key}'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = json.loads(response.content)

            # print(data)

            # Check each item in response
            for item in data:
                if item['source'] != 'bazaar':
                    continue

                print('working on item:', item['item_id'])

                profile = self.ensure_user(item['player_id'])
                if not profile:
                    continue

                item = self.map_item_id(item)

                item['owner_id'] = None
                # item['owner_id'] = profile.id
                if item.get('item_details', {}).get('rarity') != 'None':
                    self.rare_items.append(
                        self.map_item(item)
                    )

            # Add delay to respect rate limits
            return True

        except requests.RequestException:
            print(f'Error fetching details from TornPal')
            return False

    def map_item(self, item):
        bonuses = []
        for bonus in item['item_details']['bonuses'].values():
            db_bonus = self.bonuses.filter(title=bonus['bonus']).first()
            bonuses.append({
                'value': bonus['value'],
                'type': 'tick' if 'Disarm' in bonus['bonus'] else 'percentage',
                'bonus_id': db_bonus.id if db_bonus else None
            })

        return {
            'item_id': item['item_id'],
            'uid': item['uid'],
            'price': item['price'],
            'owner_id': item['owner_id'],
            'accuracy': item['item_details']['accuracy'],
            'damage': item['item_details']['damage'],
            'quality': item['item_details']['quality'],
            'rarity': item['item_details']['rarity'],
            'bonuses': bonuses,
            'created_at': datetime.now().timestamp(),
            'created_at': datetime.now().timestamp(),
            'updated_at': item['updated'],
        }

    def save_to_database(self):
        """Save all rare items and their bonuses in bulk transactions"""
        try:
            with transaction.atomic():
                # Get existing UIDs
                existing_uids = set(ItemVariation.objects.values_list('uid', flat=True))

                # Prepare ItemVariation objects
                variations = [
                    ItemVariation(
                        uid=item['uid'],
                        owner_id=item['owner_id'],
                        item_id=item['item_id'],
                        accuracy=item['accuracy'],
                        damage=item['damage'],
                        quality=item['quality'],
                        market_type='bazaar',
                        price=item['price'],
                        created_at=item['created_at'],
                        updated_at=item['updated_at'],
                        rarity=item['rarity'].capitalize(),
                        is_saleable=True
                    ) for item in self.rare_items
                    if item['uid'] not in existing_uids
                ]

                if not variations:
                    print('All items already exist in database')
                    return

                # Bulk create variations
                created_variations = ItemVariation.objects.bulk_create(variations)

                # Prepare ItemVariationBonuses objects
                all_bonuses = []
                for var, item_data in zip(created_variations, self.rare_items):
                    for bonus in item_data['bonuses']:
                        if bonus['bonus_id']:  # Only add if bonus was found in DB
                            all_bonuses.append(
                                ItemVariationBonuses(
                                    item_variation=var,
                                    bonus_id=bonus['bonus_id'],
                                    value=bonus['value'],
                                    type=bonus['type']
                                )
                            )

                # Bulk create bonuses
                ItemVariationBonuses.objects.bulk_create(all_bonuses)

                print(f"Successfully saved {len(variations)} items with {len(all_bonuses)} bonuses")

        except Exception as e:
            print(f'Error saving to database: {str(e)}')
            raise