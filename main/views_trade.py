import json
import re
import os
from typing import List
import requests
from html import escape
from itertools import islice
from collections import defaultdict

from django.conf import settings as project_settings
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q, Prefetch, Max, OuterRef, Subquery
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST

from hitcount.models import HitCount
from hitcount.views import HitCountMixin
from main.filters import CompanyListingFilter, EmployeeListingFilter, ListingFilter, ServicesFilter, ItemVariationFilter
from main.model_utils import (get_all_time_leaderboard, get_active_traders, get_changelog,
                              get_most_trades)
from main.models import Company, Item, ItemTrade, Listing, Service, Services, TradeReceipt, ItemVariation, ItemVariationBonuses
from main.profile_stats import return_profile_stats
from main.te_utils import (categories, dictionary_of_categories, get_ordered_categories, get_services_view,
                           merge_items, parse_trade_text, return_item_sets, service_categories, log_error)
from users.forms import SettingsForm
from users.models import Profile, Settings
from vote.models import Vote

@login_required
def edit_price_list(request):
    profile = (
        Profile.objects.select_related('settings').filter(user=request.user)
        .order_by('-created_at')
        .first()
    )
    
    all_traders_prices = Listing.objects.filter(owner=profile).select_related('owner', 'item', 'owner__settings').order_by('-item__TE_value')
     
    data_dict = {}
    cats = categories()
    for category in cats:
        cat_items = Item.objects.filter(
            item_type=category, circulation__gt=project_settings.MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM, TE_value__gt=10
        ).order_by('-TE_value')
        
        # add trader's data to the pool of all items
        cat_items = merge_items(cat_items, all_traders_prices)
        data_dict.update({category: cat_items})

    user_settings = profile.settings
    
    context = {
        'page_title': 'Edit Prices - Torn Exchange',
        'item_types': categories,
        'owner_profile': profile,
        'user_settings': user_settings,
        'category_dict': dictionary_of_categories(),
        'data_dict': data_dict,
    }

    if request.method == 'POST':
        updated_prices = {}
        updated_discounts = {}
        
        # first go through all categories
        for items in data_dict:
            all_relevant_items = data_dict[items]
            
            for item in all_relevant_items:
                price = request.POST.get(f'{item}_max_price')
                if price and price.strip():
                    price = re.sub(r'[$,]', '', price)
                    
                discount = (request.POST.get(f'{item}_discount'))
                
                try:
                    if discount == '' or discount is None or discount == 'None':
                        discount = ''
                    else:
                        discount = float(discount)
                except Exception as e:
                    discount = ''
                    
                try:
                    if price and price != '':
                        price = int(price)
                except Exception as e:
                    price = ''

                if type(discount) == float:
                    if discount > 100.0:
                        # prevent message alert from fading away
                        storage = messages.get_messages(request)
                        storage.used = False

                        messages.error(
                            request, 'Make sure your discount value is less than 100')
                        return redirect('edit_price_list')
                
                if price != '':
                    updated_prices.update({item: price})
                if discount != '':
                    updated_discounts.update({item: discount})

        # delete all items first
        [a.delete() for a in Listing.objects.filter(owner=profile)]
        
        # then recreate them again
        for key in updated_prices:
            Listing.objects.update_or_create(
                owner=profile,
                item=key,
                defaults={'price': updated_prices.get(key)})
        
        for key in updated_discounts:
            Listing.objects.update_or_create(
                owner=profile,
                item=key,
                defaults={'discount': updated_discounts.get(key)})

        for items in data_dict:
            all_relevant_items = data_dict[items]

            for item in all_relevant_items:
                checkbox_output = request.POST.get(f'{item}_checkbox')
                if checkbox_output == 'on':
                    try:
                        Listing.objects.get(owner=profile, item=item).delete()
                    except:
                        pass

        cache.delete(f'price_list_{profile.torn_id}')

        messages.success(request, f'Your price list has been updated!')
        return redirect('edit_price_list')
    else:
        return render(request, 'main/price_list_creation.html', context)
    
@xframe_options_exempt
def price_list(request, identifier=None):
    """Trader's public price list

    Args:
        request (HttpObject): Web request or form pOST
        identifier (string | number, optional): Can be either Torn player name or ID. Defaults to None.

    Returns:
        render: Rendered HTML template
    """
    if identifier is None:
        if request.user.is_authenticated:
            profile = (
                Profile.objects.select_related('settings').filter(user=request.user)
                .order_by('-created_at')
                .first()
            )
            
            if profile:
                return redirect(reverse('price_list', args=[profile.name]))
        
        messages.error(request, 'You first need to log in to view your price list')
        return redirect('login')

    if request.user.is_authenticated:
        profile = (
            Profile.objects.select_related('settings').filter(user=request.user)
            .order_by('-created_at')
            .first()
        )
        user_settings = profile.settings
    else:
        profile = None
        user_settings = None

    # if the torn_id for the page corresponds to an existing profile
    pricelist_profile = (
        Profile.objects.select_related('settings')
        .filter(Q(torn_id=identifier) | Q(name__iexact=identifier))
        .order_by('-created_at')
        .first()
    )

    if pricelist_profile:
        owner_settings = pricelist_profile.settings
    else:
        context = {
            'error_message': f'Oops, looks like {identifier} does not correspond to a valid pricelist! Try checking the spelling for any typos.'
        }
        return render(request, 'main/error.html', context)
    
    # COUNTING HITS
    hit_count = HitCount.objects.get_for_object(pricelist_profile)
    HitCountMixin.hit_count(request, hit_count)

    key = f'price_list_{pricelist_profile.torn_id}'
    cached_data = cache.get(key)
    if cached_data is not None:
        all_relevant_items, last_updated, last_receipt = cached_data
    else:
        all_relevant_items = Listing.objects.filter(
            owner=pricelist_profile).select_related('owner', 'item', 'owner__settings').order_by('-item__TE_value')

        last_receipt = TradeReceipt.objects.select_related('owner').filter(owner=pricelist_profile).last()

        try:
            last_updated = all_relevant_items.order_by('-item__last_updated').first().item.last_updated
        except AttributeError:
            last_updated = None

        if all_relevant_items is not None:
            cache.set(key, (all_relevant_items, last_updated, last_receipt), 60 * 60 * 1)

    distinct_categories: List[str] = list(
        all_relevant_items.values_list('item__item_type', flat=True)
        .distinct()
        .order_by('item__item_type')
    )
    
    item_types = get_ordered_categories(distinct_categories, pricelist_profile.hidden_categories, pricelist_profile.order_categories)
    
    vote_score = pricelist_profile.vote_score
    vote_count = pricelist_profile.votes.count()
    
    time_since_last_trade = getattr(last_receipt, "created_at", None)
    
    if owner_settings.trade_list_description:
        description = owner_settings.trade_list_description
    else:
        description = 'Welcome to '+pricelist_profile.name+'\'s price list. Click Start Trade now to start a trade.'
    
    context = {
        'page_type': 'trade',
        'page_title': pricelist_profile.name+'\'s Price List - Torn Exchange',
        'content_title': pricelist_profile.name+'\'s Trading List',
        'description': description,
        'items': all_relevant_items,
        'item_types': item_types,
        'owner_profile': pricelist_profile,
        'user_profile': profile,
        'vote_score': vote_score,
        'vote_count': vote_count,
        'user_settings': user_settings,
        'owner_settings': owner_settings,
        'last_updated': last_updated,
        'time_since_last_trade': time_since_last_trade,
    }

    return render(request, 'main/price_list.html', context)

@login_required
def calculator(request):
    profile = Profile.objects.filter(user=request.user).get()
    all_relevant_items = Item.objects.filter(
        listing__in=Listing.objects.filter(owner=profile)).all()
    item_types = all_relevant_items.values('item_type').distinct()
    try:
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        user_settings = None

    context = {
        'page_title': 'Calculator - Torn Exchange',
        'items': all_relevant_items,
        'user_settings': user_settings,
        'item_types': item_types,
        'owner_profile': profile,
    }
    return render(request, 'main/calculator.html', context)

# JSON response
def parse_trade_paste(request: HttpRequest):
    """Parse trade text from Calculator page and match them with trader's price list

    Args:
        request (HttpRequest): Full HTTP POST request

    Returns:
        JSON: All items, quentities and their market prices and trader prices
    """ 
    if request.method == "POST":
        username = request.POST.get('profile', '')
        profile = (
            Profile.objects.filter(name=username)
            .order_by('-created_at')
            .first()
        )
        trade_paste = (request.POST.get('prompt', None))

        if trade_paste is not None:
            name, item_list, item_quantities = parse_trade_text(trade_paste)
            
            if profile.settings.trade_enable_sets:
                item_list, item_quantities = return_item_sets(item_list, item_quantities)
            
            # Fetch all items in one query
            items = Item.objects.filter(name__in=item_list)
    
             # If no items were found, return an error
            if not items.exists():
                return JsonResponse({"error": "No items found matching the given names."}, status=400)

            # Fetch listings for the fetched items and the given profile
            listings = Listing.objects.filter(owner=profile, item__in=items)

            # Create a mapping of item names to their respective objects
            item_map = {item.name: item for item in items}

            # Create a mapping of items to their effective prices
            listing_map = {listing.item: listing.effective_price for listing in listings}
            
            price_list = []
            item_urls = []
            market_prices = []
            escaped_item_list = []
            for item_name in item_list:
                if item_name not in item_map:
                    # Item doesn't exist
                    return JsonResponse({"error": f"Item '{item_name}' does not exist."}, status=400)

                item = item_map[item_name]
                price = listing_map.get(item, 0)  # Default to 0 if no listing found
                price_list.append(price)
                
                item_urls.append(item.image_url)
                market_prices.append(item.TE_value)
                escaped_item_list.append(item_name)

            return JsonResponse({
                "name": escape(name), 
                "items": item_list, 
                "qty": item_quantities, 
                "price": price_list, 
                'market_prices': market_prices, 
                'img_url': item_urls
            }, status=200)

    return JsonResponse({}, status=400)

@csrf_exempt
def new_extension_get_prices(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_name = data.get('user_name')
            seller_name = data.get('seller_name')
            profile = (
                Profile.objects.filter(name__iexact=user_name)
                .order_by('-created_at')
                .first()
            )
            
            items = data.get('items')
            quantities = data.get('quantities')
            
            if profile.settings.trade_enable_sets:
                items, quantities = return_item_sets(items, quantities)
                
            listings = []
            items_objects = []
            
            for i in items:
                try:
                    # print(i, Listing.objects.get(owner=profile, item__name=i))
                    listings.append(Listing.objects.get(
                        owner=profile, item__name=i))
                except Listing.DoesNotExist:
                    listings.append(None)
                    
            for i in items:
                try:
                    items_objects.append(Item.objects.get(name=i))
                except Item.DoesNotExist:
                    items_objects.append(None)
                    
            prices = [a.effective_price if a is not None else 0 for a in listings]
            profit_per_item = []
            
            for i in range(len(listings)):
                try:
                    profit_per_item.append(
                        listings[i].profit_per_item*quantities[i])
                except Exception as e:
                    log_error(e)
                    profit_per_item.append(0)
                    
            image_url = [
                a.image_url if a is not None else '' for a in items_objects]
            market_values = [
                a.TE_value if a is not None else 0 for a in items_objects]
        
        except Exception as e:
            log_error(e)
            return JsonResponse({'error_message': "unknown error, please report to admin"}, status=400)

        data = {
            "seller_name": seller_name,
            "buyer_name": profile.name,
            "items": items,
            "quantities": quantities,
            "prices": prices,
            "profit_per_item": profit_per_item,
            'image_url': image_url,
            'market_prices': market_values,
        }
        
        return JsonResponse(data, status=200)

    return JsonResponse({}, status=400)

@csrf_exempt
def new_create_receipt(request):
    if request.method == "POST":
        try: 
            data = json.loads(request.body)

            item_names = data.get('item_names')
            item_quantities = data.get('item_quantities')
            item_prices = data.get('prices')
            owner_name = data.get('owner_username')
            seller_name = data.get('seller_username')
            
            owner_profile = Profile.objects.filter(name__iexact=owner_name).get()
            trade_receipt = TradeReceipt(owner=owner_profile, seller=seller_name)
            trade_receipt.save()

            for i in range(len(item_names)):
                quantity = item_quantities[i]
                price = item_prices[i]
                
                item = Item.objects.filter(name=item_names[i]).get()
                item_trade = ItemTrade(
                    owner=owner_profile, item=item, price=price, quantity=quantity, seller=seller_name)
                if item_trade.is_valid() == 'valid':
                    item_trade.save()
                    trade_receipt.items_trades.add(item_trade)
                else:
                    return JsonResponse({'error_message': item_trade.is_valid()}, status=400)
            trade_receipt.save()
            
            listings_count = TradeReceipt.objects.filter(
                owner=owner_profile, seller=seller_name
            ).count()
            trade_paste_text = owner_profile.settings.receipt_paste_text

            # error handling for when trader hasn't yet set any message in Settings:
            trade_paste_text = '' if trade_paste_text is None else trade_paste_text

            trade_paste_text = trade_paste_text.replace(
                '[[seller_name]]', seller_name)
            trade_paste_text = trade_paste_text.replace(
                '[[total]]', "${:,.0f}".format(trade_receipt.total))
            trade_paste_text = trade_paste_text.replace(
                '[[receipt_link]]', f'tornexchange.com/receipt/{trade_receipt.receipt_url_string}')
            trade_paste_text = trade_paste_text.replace(
                '[[trade_number]]', str(listings_count))
            trade_paste_text = trade_paste_text.replace(
                '[[prices_link]]', f'tornexchange.com/prices/{owner_profile.name}')
            trade_paste_text = trade_paste_text.replace(
                '[[forum_link]]', f'www.torn.com/{owner_profile.settings.link_to_forum_post}')
            
            data = {'receipt_id': trade_receipt.receipt_url_string,
                    'trade_message': escape(trade_paste_text),
                    'profit': trade_receipt.profit,
                    'total': trade_receipt.total,
                    }
            
        except Exception as e:
            log_error(e)
            return JsonResponse({'error_message': "unknown error, please report to admin"}, status=400)
        
    return JsonResponse(data=data, status=200)

def receipt_view(request, receipt_id=None):
    try:
        receipt = get_object_or_404(TradeReceipt, receipt_url_string=receipt_id)
        items_trades = receipt.items_trades.all()
        context = {
            'page_title': 'Trade Receipt - Torn Exchange',
            'receipt': receipt,
            'items_trades': items_trades,
            'sub_totals': [i.sub_total for i in items_trades],
            'total': receipt.total,
        }
        return render(request, 'main/receipt_view.html', context)
    except:
        context = {
            'error_message': 'Page not found, wrong Receipt ID in the URL'
        }
        return render(request, 'main/error.html', context)
    
def museum_helper(request):
    context = {
        'page_title': 'Zim\'s Museum Helper - Torn Exchange',
    }
    
    return render(request, 'main/museum_helper.html', context)