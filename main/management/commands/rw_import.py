import time

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


class Command(BaseCommand):
    help = 'Fetches rare items from Torn API and TornPal API'

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('SYSTEM_API_KEY')
        self.rare_items = []
        self.db_items = []
        self.max_workers = 5  # Adjust based on API rate limits
        self.timeout = 10  # seconds
        self.bonuses = ItemBonus.objects.all()
        self.items = Item.objects.all()

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

    def get_item_ids(self):
        """Fetch item IDs from Torn API for multiple categories"""
        categories = ['Primary', 'Secondary', 'Melee']
        all_item_ids = []
        
        for category in categories:
            url = 'https://api.torn.com/v2/torn/items'
            headers = {
                'accept': 'application/json',
                'Authorization': f'ApiKey {self.api_key}'
            }
            params = {
                'cat': category,
                'sort': 'DESC'
            }

            try:
                self.stdout.write(f'Fetching {category} items...')
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract IDs from response
                item_ids = [item['id'] for item in data.get('items', [])]
                all_item_ids.extend(item_ids)
                self.stdout.write(
                    self.style.SUCCESS(f'Found {len(item_ids)} {category} items')
                )
                
                # Add delay between category requests
                sleep(1)

            except requests.RequestException as e:
                self.stderr.write(
                    self.style.ERROR(f'Error fetching {category} items: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Total items found: {len(all_item_ids)}')
        )
        return all_item_ids
    
    def get_item_details(self, item_id):
        """Fetch item details from TornPal API"""
        url = f'https://tornpal.com/api/v1/bazaar/item/{item_id}'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = json.loads(response.content)
            
            # Check each item in response
            for item in data:
                profile = self.ensure_user(item['player_id'])
                if not profile:
                    continue

                item = self.map_item_id(item)

                item['owner_id'] = profile.id
                if item.get('itemdetails', {}).get('rarity') != 'None':
                    self.rare_items.append(
                        self.map_item(item)
                    )
                    
                if len(self.rare_items) > 3:
                    break
            
            # Add delay to respect rate limits
            sleep(0.5)
            return True

        except requests.RequestException:
            self.stderr.write(f'Error fetching details for item {item_id}')
            return False

    def map_item(self, item):  
        bonuses = []
        for bonus in item['itemdetails']['bonuses'].values():
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
            'accuracy': item['itemdetails']['accuracy'],
            'damage': item['itemdetails']['damage'],
            'quality': item['itemdetails']['quality'],
            'rarity': item['itemdetails']['rarity'],
            'bonuses': bonuses,
            'created_at': datetime.now().timestamp(),
            'created_at': datetime.now().timestamp(),
            'updated_at': item['updated'],
        }

    def save_to_database(self):
        """Save all rare items and their bonuses in bulk transactions"""
        try:
            with transaction.atomic():
                # Prepare ItemVariation objects
                variations = [
                    ItemVariation(
                        uid=item['uid'],
                        owner_id=item['owner_id'],
                        item_id=item['item_id'],
                        accuracy=item['accuracy'],
                        damage=item['damage'],
                        quality=item['quality'],
                        price=item['price'],
                        created_at=item['created_at'],
                        updated_at=item['updated_at'],
                        rarity=item['rarity'].capitalize(),
                        is_saleable=True
                    ) for item in self.rare_items
                ]
                
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
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully saved {len(variations)} items with '
                        f'{len(all_bonuses)} bonuses'
                    )
                )
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error saving to database: {str(e)}')
            )
            raise

    def handle(self, *args, **options):
        # Get item IDs
        self.stdout.write('Fetching item IDs...')
        item_ids = self.get_item_ids()

        if not item_ids:
            self.stderr.write('No items found')
            return

        # Process items with ThreadPoolExecutor
        self.stdout.write('Fetching item details...')
        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(self.get_item_details, item_id): item_id 
                for item_id in item_ids
            }

            for future in as_completed(future_to_id):
                item_id = future_to_id[future]
                try:
                    if future.result():
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    self.stderr.write(
                        f'Error processing item {item_id}: {str(e)}'
                    )
                    failed += 1

        print(json.dumps(self.rare_items, indent=2))

        # After collecting items, save to database
        if self.rare_items:
            self.save_to_database()
        else:
            self.stdout.write('No rare items to save')
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcess completed:\n'
                f'Total items processed: {len(item_ids)}\n'
                f'Successful: {successful}\n'
                f'Failed: {failed}\n'
                f'Rare items found: {len(self.rare_items)}'
            )
        )
        
        
        
        # Save rare items to database
        

        # Optionally save results
        # with open('rare_items.json', 'w') as f:
        #     json.dump(self.rare_items, f, indent=2)
