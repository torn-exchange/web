import pandas as pd
import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings as project_settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from main.models import Item
import time
from users.models import Profile
import numpy as np
import random
import os


class Command(BaseCommand):
    help = 'Updates items in the database'

    # checks if item name was passed as an argument
    # if not, it will update all items
    # if yes, it will update only the item passed as an argument
    def add_arguments(self, parser):
        parser.add_argument('item_name', nargs='?', type=str)

    system_api_key = os.getenv('SYSTEM_API_KEY')
    req = requests.get(
        f'https://api.torn.com/torn/?selections=items&key={system_api_key}')
    data = json.loads(req.content)['items']
    df = pd.DataFrame(data).transpose()

    def _populate(self, df=df):

        print('Updating items...')
        create_or_update_sets()
        create_or_update_basic_property()
        create_or_update_full_property()

        for index, row in df.iterrows():
            if row['circulation'] < project_settings.MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM:
                continue
            item_id = row['image'].replace(
                'https://www.torn.com/images/items/', '').replace('/large.png', '')
            # print(row)
            TE_price = get_lowest_market_price(
                item_id, get_random_key(), row['market_value'])
            # print(TE_price, '<- TE_price')
            while bool(TE_price) is not True:
                TE_price = get_lowest_market_price(
                    item_id, get_random_key(), row['market_value'])
                if TE_price == 0:
                    break
            try:
                item_in_our_db = Item.objects.get(item_id=item_id)
            except ObjectDoesNotExist:
                print("==> ObjectDoesNotExist")
                item_in_our_db = None
            except MultipleObjectsReturned:
                print("==> MultipleObjectsReturned")
                item_in_our_db = None
                    
            except Exception as e:
                item_in_our_db = None

            if (item_in_our_db != None):
                if item_in_our_db.TE_value != TE_price:
                    f'Saving {row["name"]} [{item_id}]. Market price: {row["market_value"]}, TE_price: {TE_price}'
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
                    print(
                        f'Updated {row["name"]} [{item_id}] market price to {row["market_value"]} and TE_price to {TE_price}')
            else:
                f'Saving {row["name"]} [{item_id}]. Market price: {row["market_value"]}, TE_price: {TE_price}'
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
                print(
                    f'Created {row["name"]} -{item_id} as a new entry on the db')

            # else:
            #     pass
                #    print(f'skipped {row["name"]} -{item_id} because market price is {row["market_value"]}')

        print('Done!')

    def handle(self, *args, **options):
        if options['item_name']:
            item_name = options['item_name']
            custom_df = self.df[self.df['name'] == item_name]
            print(custom_df.to_string())
            self._populate(custom_df)
        else:
            self._populate()


def get_random_key():
    key = random.choice(Profile.objects.all()).api_key
    while key == '':
        key = random.choice(Profile.objects.all()).api_key
    return key


def get_lowest_market_price(item_id, api_key, avg_market_price=np.nan):
    time.sleep(0.08)
    req = requests.get(
        f'https://api.torn.com/market/{item_id}?selections=itemmarket,bazaar&key={api_key}')
    data = json.loads(req.content)
    # print(f'using api key: {api_key}')
    if api_key != '':
        if data.get('error'):
            # print('error')
            # print(data)
            return None
        else:
            bazaar_data = data.get('bazaar')

            if bazaar_data is not None:
                try:
                    first_three = list(
                        map(lambda x: x.get('cost'), bazaar_data[:3]))
                    # print(first_three,'bazaar prices')
                    bazaar_min = np.nanmean(first_three)
                except:
                    try:
                        bazaar_min = np.mean(bazaar_data[0].get('cost'))
                    except:
                        bazaar_min = avg_market_price

            else:
                bazaar_min = np.nan

            itemmarket_data = data.get('itemmarket')
            if itemmarket_data is not None:
                try:
                    first_three = list(
                        map(lambda x: x.get('cost'), itemmarket_data[:3]))
                    # print(first_three,'itemmarket prices')
                    itemmarket_min = np.nanmean(first_three)
                except:
                    try:
                        itemmarket_min = np.mean(bazaar_data[0].get('cost'))
                    except:
                        itemmarket_min = avg_market_price

            else:
                itemmarket_min = np.nan
            # print(avg_market_price,'average_market_price')
            # print(itemmarket_min,'itemmarket_min')
            # print(bazaar_min,'bazaar_min')
            pricing_data = np.array(
                [itemmarket_min, bazaar_min, avg_market_price])
            try:
                TE_price = int(
                    round(np.nanmin(pricing_data[np.nonzero(pricing_data)])))
                # print(f'TE_price is {TE_price}')
            except Exception as e:

                print(str(e), item_id)
                TE_price = 0
            # print(TE_price,'te_price')
            return TE_price
    else:
        return None


def get_points_market_value():
    system_api_key = os.getenv('SYSTEM_API_KEY')
    req = requests.get(
        f'https://api.torn.com/market/?selections=pointsmarket&key={system_api_key}')
    data = json.loads(req.content)
    points_cost = int(round(np.nanmean(
        [data['pointsmarket'][a]['cost'] for a in data['pointsmarket']][0:5])))
    # print(points_cost)
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

def create_or_update_basic_property():
    # Trailer
    Item.objects.update_or_create(
        name='Trailer (110 happiness)',
        defaults=dict(
            item_id=9997,
            description='Trailer',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=5000,
            sell_price=5000,
            market_value=3500,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/trailer1.png',
            TE_value=3500
        ),
    )

    # Apartment
    Item.objects.update_or_create(
        name='Apartment (125 happiness)',
        defaults=dict(
            item_id=9996,
            description='Apartment',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=25000,
            sell_price=25000,
            market_value=25000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/apartment1.png',
            TE_value=25000
        ),
    )

    # Semi-Detached House
    Item.objects.update_or_create(
        name='Semi-Detached House (150 happiness)',
        defaults=dict(
            item_id=9995,
            description='Semi-Detached House',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=75000,
            sell_price=75000,
            market_value=75000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/semiDetached1.png',
            TE_value=75000
        ),
    )
    
    # Detached House
    Item.objects.update_or_create(
        name='Detached House (200 happiness)',
        defaults=dict(
            item_id=9994,
            description='Detached House',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=300000,
            sell_price=300000,
            market_value=300000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/detachedHouse1.png',
            TE_value=300000
        ),
    )
    
    # Beach House
    Item.objects.update_or_create(
        name='Beach House (300 happiness)',
        defaults=dict(
            item_id=9993,
            description='Beach House',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=500000,
            sell_price=500000,
            market_value=500000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/beachHouse1.png',
            TE_value=500000
        ),
    )

    # Chalet
    Item.objects.update_or_create(
        name='Chalet (350 happiness)',
        defaults=dict(
            item_id=9992,
            description='Chalet',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=750000,
            sell_price=750000,
            market_value=750000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/chalet1.png',
            TE_value=750000
        ),
    )

    # Villa
    Item.objects.update_or_create(
        name='Villa (400 happiness)',
        defaults=dict(
            item_id=9991,
            description='Villa',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=1250000,
            sell_price=1250000,
            market_value=1250000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/villa1.png',
            TE_value=1250000
        ),
    )

    # Penthouse
    Item.objects.update_or_create(
        name='Penthouse (450 happiness)',
        defaults=dict(
            item_id=9990,
            description='Penthouse',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=2000000,
            sell_price=2000000,
            market_value=2000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/penthouse1.png',
            TE_value=2000000
        ),
    )

    # Mansion
    Item.objects.update_or_create(
        name='Mansion (500 happiness)',
        defaults=dict(
            item_id=9989,
            description='Mansion',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=3000000,
            sell_price=3000000,
            market_value=3000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/mansion1.png',
            TE_value=3000000
        ),
    )

    # Ranch
    Item.objects.update_or_create(
        name='Ranch (600 happiness)',
        defaults=dict(
            item_id=9988,
            description='Ranch',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=15000000,
            sell_price=15000000,
            market_value=15000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/ranch1.png',
            TE_value=15000000
        ),
    )

    # Palace
    Item.objects.update_or_create(
        name='Palace (1000 happiness)',
        defaults=dict(
            item_id=9987,
            description='Palace',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=65000000,
            sell_price=65000000,
            market_value=65000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/palace1.png',
            TE_value=65000000
        ),
    )

    # Castle
    Item.objects.update_or_create(
        name='Castle (1500 happiness)',
        defaults=dict(
            item_id=9986,
            description='Castle',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=200000000,
            sell_price=200000000,
            market_value=200000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/castle1.png',
            TE_value=200000000
        ),
    )

    # Private Island
    Item.objects.update_or_create(
        name='Private Island (2000 happiness)',
        defaults=dict(
            item_id=9985,
            description='Private Island',
            requirement='',
            item_type='Basic Properties',
            weapon_type='',
            buy_price=500000000,
            sell_price=500000000,
            market_value=500000000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/island.png',
            TE_value=500000000
        ),
    )

def create_or_update_full_property():
    # Trailer
    Item.objects.update_or_create(
        name='Trailer (165 happiness)',
        defaults=dict(
            item_id=9984,
            description='Trailer',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=7500,
            sell_price=7500,
            market_value=7500,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/trailer1.png',
            TE_value=7500
        ),
    )

    # Apartment
    Item.objects.update_or_create(
        name='Apartment (188 happiness)',
        defaults=dict(
            item_id=9983,
            description='Apartment',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=37500,
            sell_price=37500,
            market_value=37500,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/apartment1.png',
            TE_value=37500
        ),
    )

    # Semi-Detached House
    Item.objects.update_or_create(
        name='Semi-Detached House (275 happiness)',
        defaults=dict(
            item_id=9982,
            description='Semi-Detached House',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=141500,
            sell_price=141500,
            market_value=141500,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/semiDetached1.png',
            TE_value=141500
        ),
    )
    
    # Detached House
    Item.objects.update_or_create(
        name='Detached House (500 happiness)',
        defaults=dict(
            item_id=9981,
            description='Detached House',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=979000,
            sell_price=979000,
            market_value=979000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/detachedHouse1.png',
            TE_value=979000
        ),
    )
    
    # Beach House
    Item.objects.update_or_create(
        name='Beach House (650 happiness)',
        defaults=dict(
            item_id=9980,
            description='Beach House',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=1279000,
            sell_price=1279000,
            market_value=1279000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/beachHouse1.png',
            TE_value=1279000
        ),
    )

    # Chalet
    Item.objects.update_or_create(
        name='Chalet (725 happiness)',
        defaults=dict(
            item_id=9979,
            description='Chalet',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=1654000,
            sell_price=1654000,
            market_value=1654000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/chalet1.png',
            TE_value=1654000
        ),
    )

    # Villa
    Item.objects.update_or_create(
        name='Villa (800 happiness)',
        defaults=dict(
            item_id=9978,
            description='Villa',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=2404000,
            sell_price=2404000,
            market_value=2404000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/villa1.png',
            TE_value=2404000
        ),
    )

    # Penthouse
    Item.objects.update_or_create(
        name='Penthouse (925 happiness)',
        defaults=dict(
            item_id=9977,
            description='Penthouse',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=3538000,
            sell_price=3538000,
            market_value=3538000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/penthouse1.png',
            TE_value=3538000
        ),
    )

    # Mansion
    Item.objects.update_or_create(
        name='Mansion (1000 happiness)',
        defaults=dict(
            item_id=9976,
            description='Mansion',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=5038000,
            sell_price=5038000,
            market_value=5038000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/mansion1.png',
            TE_value=5038000
        ),
    )

    # Ranch
    Item.objects.update_or_create(
        name='Ranch (1200 happiness)',
        defaults=dict(
            item_id=9975,
            description='Ranch',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=23288000,
            sell_price=23288000,
            market_value=23288000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/ranch1.png',
            TE_value=23288000
        ),
    )

    # Palace
    Item.objects.update_or_create(
        name='Palace (1875 happiness)',
        defaults=dict(
            item_id=9974,
            description='Palace',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=196038000,
            sell_price=196038000,
            market_value=196038000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/palace1.png',
            TE_value=196038000
        ),
    )

    # Castle
    Item.objects.update_or_create(
        name='Castle (2725 happiness)',
        defaults=dict(
            item_id=9973,
            description='Castle',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=415788000,
            sell_price=415788000,
            market_value=415788000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/castle1.png',
            TE_value=415788000
        ),
    )

    # Private Island
    Item.objects.update_or_create(
        name='Private Island (4225 happiness)',
        defaults=dict(
            item_id=9972,
            description='Private Island',
            requirement='',
            item_type='Fully Upgraded Properties',
            weapon_type='',
            buy_price=1952788000,
            sell_price=1952788000,
            market_value=1952788000,
            circulation=10000,
            image_url='https://www.torn.com/images/v2/properties/estateagent/island.png',
            TE_value=1952788000
        ),
    )
