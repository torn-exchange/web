import pandas as pd
import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings as project_settings
from django.utils import timezone
from main.models import Item
import time
from users.models import Profile
import numpy as np
from random import choice
import os
import sys
from django.db import connection, reset_queries
from main.models import Listing
from main.services.api.weav3r.marketplace_api_service import Weav3rMarketplaceApiService


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

        # Fetched once per run (not once per item) so a slow/rate-limited
        # weav3r response doesn't multiply the hourly command's runtime.
        bazaar_by_item_id = Weav3rMarketplaceApiService.get_bazaar_averages_by_item_id()

        for index, row in df.iterrows():
            if row['circulation'] < project_settings.MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM:
                continue
            item_id = row['image'].replace(
                'https://www.torn.com/images/items/', '').replace('/large.png', '')

            bazaar_average = bazaar_by_item_id.get(int(item_id))

            TE_price = get_lowest_market_price(
                item_id, get_random_key(), row['market_value'], bazaar_average)

            while bool(TE_price) is not True:
                print("Repeating requst for item:", item_id)
                TE_price = get_lowest_market_price(
                    item_id, get_random_key(), row['market_value'], bazaar_average)
                if TE_price == 0:
                    break
            
            # item_id (Torn's stable identifier) is the true identity here, not name --
            # a Torn-side rename must update this row in place rather than create a
            # phantom duplicate, so look up (and later upsert) by item_id.
            item_in_our_db = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()

            if (item_in_our_db != None):
                if item_in_our_db.TE_value != TE_price:
                    try:
                        # First time bazaar_average becomes available for this item: it's
                        # usually the lowest of the three TE_value sources, so folding it
                        # in for the first time can drop TE_value (and every discount-based
                        # listing's effective_price) in one step. Rebalance discounts to
                        # preserve traders' existing effective_price instead of letting the
                        # rollout silently move it -- a one-time transitional accommodation,
                        # not a permanent freeze; ordinary TE_value changes afterwards
                        # continue to move effective_price as they always have.
                        is_first_bazaar_average = (
                            item_in_our_db.bazaar_average is None and bazaar_average is not None
                        )

                        for key in ['buy_price', 'sell_price', 'market_value']:
                            row[key] = sanitize_numbers(row[key])
                        TE_price = sanitize_numbers(TE_price)

                        item_obj, _ = Item.objects.update_or_create(
                            item_id=item_id,
                            defaults=dict(
                                name=row['name'],
                                description=row['description'],
                                requirement=row['requirement'],
                                item_type=row['type'],
                                weapon_type=row['weapon_type'],
                                buy_price=row['buy_price'],
                                sell_price=row['sell_price'],
                                market_value=row['market_value'],
                                circulation=row['circulation'],
                                image_url=row['image'],
                                TE_value=TE_price,
                                bazaar_average=bazaar_average,
                                bazaar_fetched_at=timezone.now() if bazaar_average else None,
                            ),
                        )
                        if is_first_bazaar_average:
                            rebalance_discounts_to_preserve_effective_price(item_obj)
                        else:
                            recalculate_listings_for_item(item_obj)
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
                        item_id=item_id,
                        defaults=dict(
                            name=row['name'],
                            description=row['description'],
                            requirement=row['requirement'],
                            item_type=row['type'],
                            weapon_type=row['weapon_type'],
                            buy_price=row['buy_price'],
                            sell_price=row['sell_price'],
                            market_value=row['market_value'],
                            circulation=row['circulation'],
                            image_url=row['image'],
                            TE_value=TE_price,
                            bazaar_average=bazaar_average,
                            bazaar_fetched_at=timezone.now() if bazaar_average else None,
                        )
                    )
                except Exception as e:
                    print(e)
                    print(f'Did NOT save item: {row["name"]} [{item_id}]', row)

                print(
                    f'Created {row["name"]} -{item_id} as a new entry on the db')

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


def get_random_key():
    profiles_with_keys = Profile.objects.exclude(api_key=None).exclude(api_key='')
    if not profiles_with_keys.exists():
        return os.getenv('SYSTEM_API_KEY')

    # Select a random API key from the filtered set
    return choice(profiles_with_keys).api_key


def get_lowest_market_price(item_id, api_key, avg_market_price=np.nan, bazaar_average=None):
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

        bazaar_average = bazaar_average or np.nan

        # error handling to avoid "cannot convert float NaN to integer" error
        if all(x in [None, np.nan, 0] for x in [itemmarket_min, avg_market_price, bazaar_average]):
            return 0

        try:
            pricing_data = np.array([itemmarket_min, avg_market_price, bazaar_average])

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


def recalculate_listings_for_item(item):
    for listing in Listing.objects.filter(item=item).select_related('owner__settings', 'item'):
        listing.save(update_fields=['effective_price'])


# Discount must stay within the range accepted elsewhere (main/api.py's
# modify_listing), so a rebalance target outside it can't be represented.
MIN_DISCOUNT = -100
MAX_DISCOUNT = 100


def rebalance_discounts_to_preserve_effective_price(item):
    """
    Recalculates the `discount` on every discount-based Listing for `item` so
    that `effective_price` stays exactly where it was before `item.TE_value`
    just changed, instead of drifting down with it. Fixed-price-only listings
    (discount is None) are untouched, since they were never driven by
    TE_value in the first place.

    This must be called with `item` already saved with its NEW TE_value, and
    relies on each Listing's `effective_price` still holding the value that
    was computed under the OLD TE_value (true as long as nothing else has
    saved these Listings in between).

    Works for all three listing shapes uniformly: discount-only (effective_price
    is the discount price, which gets recalculated to match itself); discount+price
    where discount was binding (same as discount-only); and discount+price where
    the fixed price was binding (the new discount price is set to exactly equal
    price, so `min(discount_price, price)` still resolves to `price`).
    """
    for listing in Listing.objects.filter(item=item, discount__isnull=False).select_related('owner__settings'):
        old_effective_price = listing.effective_price
        if old_effective_price is None or not item.TE_value:
            # Nothing to preserve, or TE_value is 0/None so no discount can hit
            # a nonzero target -- leave the listing for normal recalculation.
            continue

        global_fee = listing.owner.settings.trade_global_fee or 0
        if item.item_id > 9000:
            global_fee = 0

        new_discount = 100.0 - global_fee - (old_effective_price / item.TE_value * 100.0)

        if new_discount < MIN_DISCOUNT or new_discount > MAX_DISCOUNT:
            print(
                f'Skipping discount rebalance for Listing {listing.id}: required discount '
                f'{new_discount:.2f}% is outside the [{MIN_DISCOUNT}, {MAX_DISCOUNT}] range'
            )
            continue

        listing.discount = round(new_discount, 4)
        listing.save(update_fields=['discount', 'effective_price'])

        # Up to ~0.1% rounding drift is expected/accepted; anything more suggests a bug.
        new_effective_price = listing.effective_price or 0
        drift = abs(new_effective_price - old_effective_price)
        tolerance = max(1, abs(old_effective_price) * 0.001)
        if drift > tolerance:
            print(
                f'WARNING: Listing {listing.id} drifted by {drift} after discount rebalance '
                f'(old effective_price={old_effective_price}, new={new_effective_price})'
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

