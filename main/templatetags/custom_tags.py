import json
from html import unescape

from django.db.models.query import QuerySet
from django.core.serializers import serialize
from ..models import Listing
from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.simple_tag(name='listing_price')
def prepopulate_listing_price(item, profile):
    try:
        listing = Listing.objects.filter(owner=profile, item=item).get()
        if listing.price > 0:
            return listing.price
        else:
            return ''
    except:
        return ''


@register.simple_tag(name='listing_discount')
def prepopulate_listing_discount(item, profile):
    try:
        listing = Listing.objects.filter(owner=profile, item=item).get()
        if listing.discount is None:
            return ''
        return listing.discount
    except:
        return ''


@register.filter(name='buy_price')
def buy_price(item, profile):
    listing = Listing.objects.filter(owner=profile, item=item).get()
    return listing.effective_price


@register.filter(name='item_plurals')
def item_name_plural(item_name):
    if item_name == 'Defensive':
        return 'Armor'
    if item_name in ['Drug', 'Tool', 'Material', 'Car', 'Flower', 'Plushie', 'Booster', 'Enhancer', 'Artifact', 'Energy Drink']:
        return item_name+'s'
    if item_name == 'Other':
        return 'Miscellaneous'
    return item_name


@register.filter(name='listing_updated')
def listing_last_updatedupdated(item, profile):
    listing = Listing.objects.filter(owner=profile, item=item).get()
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
    return string.replace(' ', '_')


@register.simple_tag(name='get_dict_entry')
def get_dict_entry(dict, entry):
    return dict[entry]


@register.simple_tag(name='calculate_effective_price')
def calculate_effective_price(item, profile):
    try:
        listing = Listing.objects.filter(owner=profile, item=item).get()
        return listing.effective_price
    except:
        return ''


@register.filter
def time_since(value):
    # Returns a string representing "time since" the given datetime.
    if not value:
        return ""
    
    now = timezone.now()

    # If the value is in the future, return an appropriate message
    if value > now:
        return "just now"

    # Get the time difference in a human-readable format
    time_diff = timesince(value, now)

    # Format to display as "X time ago"
    return f"{time_diff.split(', ')[0]} ago"


@register.filter(name='sanitize_number')
def sanitize_number(value):
    return f"${value:,}" if value > 0 else ''


@register.filter(name='sanitize_string')
def sanitize_string(value):
    return unescape(value)


@register.simple_tag()
def prepopulate_service_money(service, user_services):
    try:
        for user_service in user_services:
            if service.name == user_service.service.name:
                return f"${user_service.money_price:,}" if user_service.money_price > 0 else ''
    
    except Exception as e:
        print("custom tag: service money. Error: ", e)
        return ''
    
    return ''


@register.simple_tag()
def prepopulate_service_barter(service, user_services):
    try:
        for user_service in user_services:
            if service.name == user_service.service.name:
                return unescape(user_service.barter_price)
    
    except Exception as e:
        print("custom tag: service_barter. Error: ", e)
        return ''
    
    return ''


@register.simple_tag()
def prepopulate_service_desc(service, user_services):
    try:
        for user_service in user_services:
            if service.name == user_service.service.name:
                return unescape(user_service.offer_description)
    
    except Exception as e:
        print("custom tag: service_desc. Error: ", e)
        return ''
    
    return ''
