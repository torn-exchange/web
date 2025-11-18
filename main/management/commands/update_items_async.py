import requests
import json
import random
import os
import sys
import time
import  concurrent.futures
import pandas as pd
import numpy as np

from django.db import connection, reset_queries
from django.core.management.base import BaseCommand
from django.conf import settings as project_settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from main.models import Item
from users.models import Profile
from random import choice

class Command(BaseCommand):
    help = 'Updates items in the database'

    # checks if item name was passed as an argument
    # if not, it will update all items
    # if yes, it will update only the item passed as an argument
    def add_arguments(self, parser):
        parser.add_argument('item_name', nargs='?', type=str)

    system_api_key = os.getenv('SYSTEM_API_KEY')
    comment = os.getenv("API_COMMENT")
    url = f'https://api.torn.com/torn/?selections=items&key={system_api_key}{comment}'
    req = requests.get(url)
    data = json.loads(req.content)['items']
    df = pd.DataFrame(data).transpose()

    def _populate(self, df=df):
        print('Updating items...')
        create_or_update_sets()
        
        keys = Profile.objects.exclude(api_key='')
        
        # max number of threads to use
        MAX_THREADS = 4

        def process_row(index_row):
            index, row = index_row
            process_item(row, random.choice(keys).api_key)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                executor.map(process_row, df.iterrows())
        except KeyboardInterrupt:
            print("Process interrupted by user. Shutting down...")
            executor.shutdown(wait=False)
            sys.exit(1)
        
        print('Done!')
        print("Total database queries:", len(connection.queries))

    def handle(self, *args, **options):
        reset_queries()
        if options['item_name']:
            item_name = options['item_name']
            custom_df = self.df[self.df['name'] == item_name]
            print(custom_df.to_string())
            self._populate(custom_df)
        else:
            self._populate()


def process_item(row, key):
    try:
        if row['circulation'] < project_settings.MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM:
            return None
        item_id = row['image'].replace(
            'https://www.torn.com/images/items/', '').replace('/large.png', '')
        
        TE_price = get_lowest_market_price(
            item_id, key, row['market_value'])
        
        while bool(TE_price) is not True:
            print("Repeating requst for item:", item_id)
            TE_price = get_lowest_market_price(
                item_id, key, row['market_value'])
            if TE_price == 0:
                break
        
        try:
            item_in_our_db = Item.objects.get(item_id=item_id)
        except ObjectDoesNotExist:
            print("==> ObjectDoesNotExist", item_id)
            item_in_our_db = None
        except MultipleObjectsReturned:
            print("==> MultipleObjectsReturned", item_id)
            item_in_our_db = None
        except Exception as e:
            print("general exception", e)
            item_in_our_db = None

        if (item_in_our_db != None):
            if item_in_our_db.TE_value != TE_price:
                try:
                    for key in ['buy_price', 'sell_price', 'market_value']:
                        row[key] = sanitize_numbers(row[key])
                    TE_price = sanitize_numbers(TE_price)

                    Item.objects.update_or_create(
                        name=row['name'],
                        defaults=dict(
                            item_id=item_id,
                            description=row['description'],
                            requirement=row['requirement'],
                            item_type=row['type'],
                            weapon_type=row['weapon_type'],
                            buy_price=row['buy_price'],
                            sell_price=row['sell_price'],
                            market_value=row['market_value'],
                            circulation=row['circulation'],
                            image_url=row['image'],
                            TE_value=TE_price
                        ),
                    )
                except Exception as e:
                    print(e)
                    print(f'Did NOT save item: {row["name"]} [{item_id}]', row)

                print(
                    f'Updated {row["name"]} [{item_id}] market price to {row["market_value"]} and TE_price to {TE_price}')
            
            print(
                f'No updated needed for {row["name"]} [{item_id}]'
            )
        else:
            try:
                for key in ['buy_price', 'sell_price', 'market_value']:
                    row[key] = sanitize_numbers(row[key])
                TE_price = sanitize_numbers(TE_price)
                
                Item.objects.update_or_create(
                    name=row['name'],
                    defaults=dict(
                        item_id=item_id,
                        description=row['description'],
                        requirement=row['requirement'],
                        item_type=row['type'],
                        weapon_type=row['weapon_type'],
                        buy_price=row['buy_price'],
                        sell_price=row['sell_price'],
                        market_value=row['market_value'],
                        circulation=row['circulation'],
                        image_url=row['image'],
                        TE_value=TE_price
                    )
                )
            except Exception as e:
                print(e)
                print(f'Did NOT save item: {row["name"]} [{item_id}]', row)

            print(
                f'Created {row["name"]} -{item_id} as a new entry on the db')
    
    except Exception as e:
        print('Request failed due to error:', e)


def get_lowest_market_price(item_id, api_key, avg_market_price=np.nan):
    if api_key == '':
        return None
    
    time.sleep(0.05)
    comment = os.getenv("API_COMMENT")
    url = f'https://api.torn.com/v2/market/?selections=itemmarket&id={item_id}&key={api_key}{comment}'
    req = requests.get(url)
    data = json.loads(req.content)

    if data.get('error'):
        print("update_items2 ERROR", data, item_id)
        
        if "Too many requests" in data["error"].get("error", ""):
            print("Rate limit hit. Waiting 30 seconds before retrying...")
            time.sleep(30)  # wait before retry
            return None  # retry the same request
        return None
    else:
        itemmarket_data = data.get('itemmarket')
        if (itemmarket_data is not None and itemmarket_data["listings"]):
            try:
                first_three = list(
                    map(lambda x: x.get('price'), itemmarket_data["listings"][:3]))
                itemmarket_min = np.nanmean(first_three)
            except Exception as e:
                print("ERROR", e, "itemID:", item_id)
                itemmarket_min = avg_market_price
        else:
            itemmarket_min = np.nan
            
        # error handling to avoid "cannot convert float NaN to integer" error
        if all(x in [None, np.nan, 0] for x in [itemmarket_min, avg_market_price]):
            return 0

        try:
            pricing_data = np.array([itemmarket_min, avg_market_price])
            
            TE_price = int(
                round(np.nanmin(pricing_data[np.nonzero(pricing_data)])))
        except Exception as e:
            print("update_items2 ERROR", str(e), item_id)
            TE_price = 0

        return TE_price


def get_points_market_value():
    system_api_key = os.getenv('SYSTEM_API_KEY')
    comment = os.getenv("API_COMMENT")
    req = requests.get(
        f'https://api.torn.com/market/?selections=pointsmarket&key={system_api_key}{comment}')
    data = json.loads(req.content)
    points_cost = int(round(np.nanmean(
        [data['pointsmarket'][a]['cost'] for a in data['pointsmarket']][0:5])))
    return points_cost


def create_or_update_sets():
    points_cost = get_points_market_value()
    Item.objects.update_or_create(
        name='Plushie Set',
        defaults=dict(
            item_id=9998,
            description='A set of plushies',
            requirement='',
            item_type='Plushie',
            weapon_type='',
            buy_price=450000,
            sell_price=450000,
            market_value=10*points_cost,
            circulation=10000,
            image_url='https://i.imgur.com/AwOwIe9.png',
            TE_value=10*points_cost
        ),
    )
    Item.objects.update_or_create(
        name='Flower Set',
        defaults=dict(
            item_id=9999,
            description='A set of flowers',
            requirement='',
            item_type='Flower',
            weapon_type='',
            buy_price=450000,
            sell_price=450000,
            market_value=10*points_cost,
            circulation=100000,
            image_url='https://i.imgur.com/ASKbyVY.png',
            TE_value=10*points_cost
        ),
    )


def sanitize_numbers(number):
    # Dirty Bomb is most expensive thing in Torn and it costs around 50B
    # so let 100B be the most expensive price possible
    if number == None:
        return 0
    
    max_price = 100000000000
    if number >= sys.maxsize - 1:
        number = max_price

    return number
