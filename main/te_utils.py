import re
from datetime import datetime
from typing import List, OrderedDict, Tuple
from django.db.models.query import QuerySet

from main.models import Service


def categories():
    return [
        'Plushie',
        'Flower',
        'Drug',
        'Energy Drink',
        'Booster',
        'Alcohol',
        'Medical',
        'Temporary',
        'Candy',
        'Special',
        'Supply Pack',
        'Enhancer',
        'Tool',
        'Material',
        'Clothing',
        'Jewelry',
        'Car',
        'Artifact',
        'Other',
        'Primary',
        'Secondary',
        'Melee',
        'Defensive', # this is Armor
        'Basic Properties',
        'Fully Upgraded Properties',
    ]


def dictionary_of_categories():
    return {
        'Equipment': ['Melee', 'Primary', 'Secondary', 'Defensive'],
        'Useful Supplies': ['Medical', 'Temporary', 'Energy Drink', 'Candy', 'Drug', 'Enhancer', 'Alcohol', 'Booster'],
        'General Shopping': ['Material', 'Jewelry', 'Tool', 'Flower', 'Supply Pack', 'Clothing', 'Car', 'Artifact', 'Plushie', 'Special', 'Other'],
        'Estate Agency': ['Basic Properties', 'Fully Upgraded Properties'],
    }
    

def service_categories():
    return [
        'Torn feature',
        'Company specials',
        'Software',
        'Attacking',
        'Custom services',
        'Other'
    ]


def service_names():
    return [
        'Bookie Tips', 
        'Racing Assistant', 
        'Reviving', 
        'Stocks Advice', 
        'View anonymous bounties', 
        'Hack a company\'s bank account', 
        'Company productivity boost', 
        'Flight Delay', 
        'See Friends & Enemies', 
        'View Money on Hand', 
        'View Stats & Money', 
        'True Level Reveal', 
        'Stat Spies', 
        'Creating Discord Bots', 
        'General Coding', 
        'Scripting', 
        'Discord Administration', 
        'Custom Spreadsheets', 
        'Selling Escapes', 
        'Selling Losses', 
        'Selling Stalemates', 
        'Mercenary', 
        'Graphics', 
        'RW Armor', 
        'RW Weapons', 
        'Other', 
    ]

def return_item_sets(item_names, item_quantities):
    item_dict = {}
    for index, value in enumerate(item_names):
        if item_dict.get(value):
            item_dict[value] += item_quantities[index]
        else:
            item_dict.update({value: item_quantities[index]})
            
    flower_set = ['African Violet', 'Banana Orchid', 'Cherry Blossom', 'Ceibo Flower',
                  'Crocus', 'Dahlia', 'Edelweiss', 'Heather', 'Orchid', 'Peony', 'Tribulus Omanense']
    plushie_set = ['Camel Plushie', 'Chamois Plushie', 'Jaguar Plushie', 'Kitten Plushie', 'Lion Plushie', 'Monkey Plushie',
                   'Nessie Plushie', 'Panda Plushie', 'Red Fox Plushie', 'Sheep Plushie', 'Stingray Plushie', 'Teddy Bear Plushie', 'Wolverine Plushie']

    while sublist(flower_set, item_dict.keys()):
        for flower in flower_set:
            item_dict[flower] -= 1
        if item_dict.get('Flower Set'):
            item_dict['Flower Set'] += 1
        else:
            item_dict.update({'Flower Set': 1})
        item_dict = dict((k, v) for k, v in item_dict.items() if v)

    while sublist(plushie_set, item_dict.keys()):
        for plushie in plushie_set:
            item_dict[plushie] -= 1
        if item_dict.get('Plushie Set'):
            item_dict['Plushie Set'] += 1
        else:
            item_dict.update({'Plushie Set': 1})
        item_dict = dict((k, v) for k, v in item_dict.items() if v)

    return list(item_dict.keys()), list(item_dict.values())


def sublist(lst1, lst2):
    return set(lst1) <= set(lst2)


def parse_trade_text(trade_text: str) -> Tuple[str, List, List]:
    """
        Parses trade text into a tuple containing the item names and the quantities
    """
    name = re.findall(r".*(?=added)", trade_text)[0].strip()
    normalised_string = trade_text.strip(' ').replace(
        'to the trade.', '').replace(name, '').replace('added', '').strip()
    quantities = [int(a.replace(', ', '')) for a in re.findall(
        r',{0,1}\s\d{1,13}(?=x\s[a-zA-Z])', trade_text)]
    items = []
    for quantity, item_string in zip(quantities, normalised_string.split(',')):
        item = item_string.replace(f'{quantity}x ', '').strip()
        items.append(item)
    return (name, items, quantities)


# debug function that outputs time in seconds with custom string
def tt(input):
    now = datetime.now()
    str = f'{now.hour}:{now.minute}:{now.second} - {input}'
    print(str)


def merge_items(all_relevant_items: QuerySet, traders_items: QuerySet):
    """Function that merges two QuerySets so that template engine doesn't have to
    request it from DB

    Args:
        all_relevant_items (QuerySet): All items available in DB
        traders_items (QuerySet): All items for which a trader has set any value

    Returns:
        QuerySet: merged items
    """
    for item in all_relevant_items:
        item.price = ""
        item.discount = ""
        item.effective_price = ""
        
        for trader_item in traders_items:
            if trader_item.item.item_id == item.item_id:
                item.price = trader_item.price if trader_item.price is not None else ''
                item.discount = trader_item.discount if trader_item.discount is not None else ''
                item.effective_price = trader_item.effective_price if trader_item.effective_price is not None else ''
                break
        
    return all_relevant_items


def get_services_view(selected_services) -> dict:
    """Returns list of Service items to display on Search Services page as Django Filter.
        It constructs a dict object and groups services by category and also attaches selected
        state by each service.
    
    Args:
        selected_services (list[str]): all checkbox'ed services from query URL
        
    Returns:
        dict: services grouped by categories
    """
    
    list_of_services = Service.objects.all().order_by("name")
    
    # Group services by category
    services_choices_unsorted = {}
    for service in list_of_services:
        category = service.category
        if category not in services_choices_unsorted:
            services_choices_unsorted[category] = []
        
        # Check if this service is in the selected services list
        checked_state = 'checked' if service.name in selected_services else ''
        services_choices_unsorted[category].append((service.name, checked_state))
        
    SERVICES_CHOICES = OrderedDict(sorted(services_choices_unsorted.items()))
    
    return SERVICES_CHOICES
