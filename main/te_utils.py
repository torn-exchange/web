import re
from typing import List, Tuple


def categories():
    categories = [
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
        'Virus',
        'Jewelry',
        'Melee',
        'Primary',
        'Secondary',
        'Defensive',
        'Clothing',
        'Electronic',
        'Car',
        'Artifact',
        'Other']

    return categories


def dictionary_of_categories():
    dictionary_of_categories ={
        'Equipment':['Melee','Primary','Secondary','Defensive'],
        'Useful Supplies':['Medical','Temporary','Energy Drink','Candy','Drug','Enhancer','Alcohol','Booster'],
        'General Shopping':['Electronic','Jewelry','Virus','Flower','Supply Pack','Clothing','Car','Artifact','Plushie', 'Special','Other'],
    }
    return dictionary_of_categories



def return_item_sets(item_names,item_quantities):
    print(item_names, item_quantities)
    item_dict = {}
    for index, value in enumerate(item_names):
        if item_dict.get(value):
            item_dict[value] += item_quantities[index]
        else:
            item_dict.update({value:item_quantities[index]})
    flower_set = ['African Violet','Banana Orchid','Cherry Blossom','Ceibo Flower','Crocus','Dahlia','Edelweiss','Heather','Orchid','Peony','Tribulus Omanense']
    plushie_set = ['Camel Plushie','Chamois Plushie','Jaguar Plushie','Kitten Plushie','Lion Plushie','Monkey Plushie','Nessie Plushie','Panda Plushie','Red Fox Plushie','Sheep Plushie','Stingray Plushie','Teddy Bear Plushie','Wolverine Plushie']
    #print(item_names, item_quantities)
    #print(item_dict)

    while sublist(flower_set,item_dict.keys()):
        for flower in flower_set:
            item_dict[flower]-= 1
        if item_dict.get('Flower Set'):
            item_dict['Flower Set']+= 1
        else:
            item_dict.update({'Flower Set':1})
        item_dict = dict((k, v) for k, v in item_dict.items() if v)
    
    while sublist(plushie_set,item_dict.keys()):
        for plushie in plushie_set:
            item_dict[plushie]-= 1
        if item_dict.get('Plushie Set'):
            item_dict['Plushie Set']+= 1
        else:
            item_dict.update({'Plushie Set':1})
        item_dict = dict((k, v) for k, v in item_dict.items() if v)

    return list(item_dict.keys()), list(item_dict.values())


def sublist(lst1, lst2):
    return set(lst1) <= set(lst2)


def parse_trade_text(trade_text: str) -> Tuple[str,List,List]:
    """
        Parses trade text into a tuple containing the item names and the quantities
    """
    print(trade_text)
    name = re.findall(r".*(?=added)", trade_text)[0].strip()
    normalised_string = trade_text.strip(' ').replace('to the trade.','').replace(name,'').replace('added','').strip()
    quantities = [int(a.replace(', ','')) for a in re.findall(r',{0,1}\s\d{1,13}(?=x\s[A-Z])',trade_text)]
    items = []
    for quantity, item_string  in  zip(quantities,normalised_string.split(',')):
        print(quantity, item_string)
        item = item_string.replace(f'{quantity}x ','').strip()
        items.append(item)
    print(name)
    print(quantities)
    print(items)
    return (name, items, quantities)