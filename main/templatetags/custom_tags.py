from django import template 
register = template.Library() 
from users.models import Profile 
from django.contrib.auth.models import User
from ..models import Listing
from ..models import Item
import numpy as np
from django.core.serializers import serialize
from django.db.models.query import QuerySet
import json
from django.template import Library

@register.simple_tag(name='listing_price')
def prepopulate_listing_price(item, profile): 
    try:
        listing = Listing.objects.filter(owner = profile, item=item).get()
        if listing.price > 0:
            return listing.price
        else:
            return ''
    except:
        return ''
@register.simple_tag(name='listing_discount')
def prepopulate_listing_discount(item, profile): 
    try:
        listing = Listing.objects.filter(owner = profile, item=item).get()
        return listing.discount
    except:
        return ''

@register.filter(name='buy_price')
def buy_price(item, profile): 
    listing = Listing.objects.filter(owner = profile, item=item).get()
    return listing.effective_price

@register.filter(name='item_plurals')
def item_name_plural(item_name):
    if item_name =='Defensive':
        return 'Armor'
    if item_name =='Virus':
        return 'Viruses'
    if item_name in ['Drug','Electronic','Car','Flower','Plushie','Booster','Enhancer','Artifact','Energy Drink']:
        return item_name+'s'
    if item_name == 'Other':
        return 'Miscellaneous'
    return item_name

@register.filter(name='listing_updated')
def listing_last_updatedupdated(item, profile): 
    listing = Listing.objects.filter(owner = profile, item=item).get()
    return listing.last_updated
    
@register.simple_tag(name='item_type_relevant')
def is_item_type_relevant(item):
    if item.item_type in ['Melee']:
        return True
    else:
        return False

@register.filter(name='jsonify')
def jsonify(object):
    if isinstance(object, QuerySet):
        return serialize('json', object)
    return json.dumps(object)


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Return encoded URL parameters that are the same as the current
    request's parameters, only with the specified GET parameters added or changed.

    It also removes any empty parameters to keep things neat,
    so you can remove a parm by setting it to ``""``.

    For example, if you're on the page ``/things/?with_frosting=true&page=5``,
    then

    <a href="/things/?{% param_replace page=3 %}">Page 3</a>

    would expand to

    <a href="/things/?with_frosting=true&page=3">Page 3</a>

    Based on
    https://stackoverflow.com/questions/22734695/next-and-before-links-for-a-django-paginated-query/22735278#22735278
    """
    d = context['request'].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    for k in [k for k, v in d.items() if not v]:
        del d[k]
    return d.urlencode()

@register.filter
def get_index(l, i):
    return l[i]
@register.filter(name='replace_spaces')
def replace_spaces(string):
    return string.replace(' ','_')

@register.simple_tag(name='get_dict_entry')
def get_dict_entry(dict, entry):
    return dict[entry]


@register.simple_tag(name='effective_price')
def effective_price(item, profile):
    try:
        listing = Listing.objects.filter(owner = profile, item=item).get()
        return listing.effective_price
    except:
        return ''