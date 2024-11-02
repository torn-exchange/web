from django.core.management.base import BaseCommand
from main.models import Item
from django.db import connection, reset_queries


class Command(BaseCommand):
    help = 'Updates items in the database'
    
    def handle(self, *args, **options):
        reset_queries()
        print('Updating properties...')
        
        create_or_update_basic_property()
        # create_or_update_full_property()
        
        print('Done!')
        print("Total database queries:", len(connection.queries))
        
        # for query in connection.queries:
        #     print(query['sql'])

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
