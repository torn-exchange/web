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
from django.db.models import F, Q
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST

from hitcount.models import HitCount
from hitcount.views import HitCountMixin
from main.filters import CompanyListingFilter, EmployeeListingFilter, ListingFilter, ServicesFilter
from main.model_utils import (get_all_time_leaderboard, get_active_traders, get_changelog,
                              get_most_trades)
from main.models import Company, Item, ItemTrade, Listing, Service, Services, TradeReceipt
from main.profile_stats import return_profile_stats
from main.te_utils import (categories, dictionary_of_categories, get_ordered_categories, get_services_view,
                           merge_items, parse_trade_text, return_item_sets, service_categories, log_error)
from users.forms import SettingsForm
from users.models import Profile, Settings
from vote.models import Vote


def homepage(request):
    cached_data = cache.get('hompeage_data')
    
    if cached_data:
        # Unpack the cached data
        all_time_traders, active_traders, most_receipts, created_today, changes_this_week, changes_this_month = cached_data
    else:
        # Compute the data if not available in the cache
        all_time_traders = get_all_time_leaderboard()
        active_traders = get_active_traders()
        most_receipts = get_most_trades()
        created_today, changes_this_week, changes_this_month = get_changelog()
        
        # Cache the computed data
        cache.set('hompeage_data', (all_time_traders, active_traders, most_receipts, created_today, changes_this_week, changes_this_month), 60*60*1)
     
    try:
        profile = Profile.objects.select_related('settings').get(user=request.user)
        user_settings = profile.settings
    except:
        profile = None
        user_settings = None

    context = {
        'profile': profile,
        'user_settings': user_settings,
        'top_50': all_time_traders,
        'most_receipts': most_receipts,
        'active_traders': active_traders,
        'created_today': created_today,
        'changelog': changes_this_week,
        'number_of_changes_last_month': changes_this_month.count(),
    }
    
    return render(request, 'main/home.html', context)


def about(request):
    context = {
        'page_title': 'About - Torn Exchange',
    }
    
    return render(request, 'main/about.html', context)


def listings(request):
    queryset = Listing.objects.all().select_related('owner', 'item').order_by('-last_updated')
    myFilter = ListingFilter(request.GET, queryset=queryset)

    try:
        query_set = myFilter.qs
        
        # exclude Listings where price is None or 0
        query_set = query_set.exclude(traders_price__isnull=True)
        number_of_items = query_set.count()

        # Attempt to get the user's profile
        if request.user.is_authenticated:
            profile = Profile.objects.filter(user=request.user).get()
            user_settings = Settings.objects.filter(owner=profile).get()
        else:
            user_settings = None
            profile = None

        paginator = Paginator(query_set, 20)
        page = request.GET.get('page')
        results = paginator.get_page(page)

    except Exception as e:
        log_error(e)
        profile = None
        user_settings = None
        results = None
        page = None
        number_of_items = None

    context = {
        'page_title': 'Search Traders - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'user_profile': profile,
        'myFilter': myFilter,
        'number_of_items': number_of_items,
    }

    return render(request, 'main/listings.html', context)


def search_services(request: HttpRequest):
    queryset = Services.objects.all()
    myFilter = ServicesFilter(request.GET, queryset=queryset)
    
    # Get all selected services from the GET request
    selected_services = request.GET.getlist('service')

    try:
        query_set = myFilter.qs
        
        # exclude Listings where price is None or 0
        number_of_items = query_set.count()

        # Attempt to get the user's profile
        if request.user.is_authenticated:
            profile = Profile.objects.filter(user=request.user).get()
            user_settings = Settings.objects.filter(owner=profile).get()
        else:
            user_settings = None
            profile = None

        paginator = Paginator(query_set, 20)
        page = request.GET.get('page')
        results = paginator.get_page(page)

    except Exception as e:
        log_error(e)
        profile = None
        user_settings = None
        results = None
        page = None
        number_of_items = None
    
    context = {
        'page_title': 'Search Services - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'user_profile': profile,
        'myFilter': myFilter,
        'order_by': request.GET.get('order_by'),
        'number_of_items': number_of_items,
        'services_by_category': get_services_view(selected_services),
    }

    return render(request, 'main/search_services.html', context)


def employee_listings(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        profile = None
        user_settings = None
    queryset = Profile.objects.filter(
        settings__job_seeking=True).all().order_by('last_active')
    myFilter = EmployeeListingFilter(request.GET, queryset=queryset)
    qs = myFilter.qs
    paginator = Paginator(qs, 8)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    number_of_items = qs.count()
    
    context = {
        'page_title': 'Search Employees - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'number_of_items': number_of_items,
        'myFilter': myFilter,
    }
    return render(request, 'main/employee_listings.html', context)


def company_listings(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        profile = None
        user_settings = None
    queryset = Company.objects.filter(
        owner__settings__selling_company=True).order_by('-rating')
    myFilter = CompanyListingFilter(request.GET, queryset=queryset)
    qs = myFilter.qs
    paginator = Paginator(qs, 4)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    number_of_items = qs.count()
    
    context = {
        'page_title': 'Companies for sale - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'number_of_items': number_of_items,
        'myFilter': myFilter,
    }
    return render(request, 'main/company_listings.html', context)


def company_hiring_listings(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        profile = None
        user_settings = None
    queryset = Company.objects.filter(
        owner__settings__company_looking_to_hire=True).all().order_by('-rating')
    myFilter = CompanyListingFilter(request.GET, queryset=queryset)
    qs = myFilter.qs
    paginator = Paginator(qs, 4)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    number_of_items = qs.count()
    
    context = {
        'page_title': 'Company recruitment - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'number_of_items': number_of_items,
        'myFilter': myFilter,
    }
    return render(request, 'main/companies_hiring.html', context)


def revives_listings(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()

    except:
        profile = None
        user_settings = None

    revivers = Profile.objects.filter(settings__selling_revives=True).all(
    ).order_by(F('last_active').desc(nulls_last=True))
    paginator = Paginator(revivers, 16)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    number_of_items = revivers.count()
    
    context = {
        'page_title': 'Revives market - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'number_of_items': number_of_items,
    }
    return render(request, 'main/revives_listings.html', context)


def losses_listings(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        profile = None
        user_settings = None

    loss_sellers = Profile.objects.filter(settings__selling_losses=True).all(
    ).order_by(F('last_active').desc(nulls_last=True))
    paginator = Paginator(loss_sellers, 16)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    number_of_items = loss_sellers.count()
    
    context = {
        'page_title': 'Loss selling - Torn Exchange',
        'user_settings': user_settings,
        'listings': results,
        'number_of_items': number_of_items,
    }
    return render(request, 'main/losses_listings.html', context)


@login_required
def settings(request, option=None):
    profile = Profile.objects.filter(user=request.user).get()
    user_settings = Settings.objects.filter(owner=profile).get()
    instance = get_object_or_404(Settings, owner=profile)
    form = SettingsForm(request.POST or None, instance=instance, initial={
        'receipt_paste_text': instance.receipt_paste_text,
        'trade_list_description': instance.trade_list_description,
        'receipt_paste_text': instance.receipt_paste_text,
    })

    context = {
        'page_title': 'Settings - Torn Exchange',
        'form': form,
        'user_settings': user_settings,
    }

    if form.is_valid():
        form.save()
        messages.success(request, 'Your settings have been updated')
    return render(request, 'main/settings.html', context)


@login_required
def edit_price_list(request):
    profile = (
        Profile.objects.select_related('settings').filter(user=request.user)
        .order_by('-created_at')
        .first()
    )
    
    all_traders_prices = Listing.objects.filter(owner=profile).select_related('item').order_by('-item__TE_value')
     
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
    
    cached_data = cache.get(f'price_list_{pricelist_profile.torn_id}')
    if cached_data:
        # Unpack the cached data
        all_relevant_items, last_updated, last_receipt = cached_data
    else:
        # Compute the data if not available in the cache
        all_relevant_items = Listing.objects.filter(
            owner=pricelist_profile).select_related('owner', 'item').order_by('-item__TE_value')
        
        last_receipt = TradeReceipt.objects.select_related('owner').filter(owner=pricelist_profile).last()
        
        try:
            last_updated = all_relevant_items.order_by('-item__last_updated').first().item.last_updated
        except AttributeError:
            last_updated = None
        
        # Cache the computed data
        cache.set(f'price_list_{pricelist_profile.torn_id}', (all_relevant_items, last_updated, last_receipt), 60*60*1)
    
    distinct_categories: List[str] = list(
        all_relevant_items.values_list('item__item_type', flat=True)
        .distinct()
        .order_by('item__item_type')
    )
    
    # item_types = [x for x in categories() if (x in distinct_categories)]
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
def edit_services(request):
    try:
        profile = Profile.objects.filter(user=request.user).get()  
    except:
        context = {
            'error_message': 'Page not found'
        }
        return render(request, 'main/error.html', context)
    
    cats = service_categories()
    user_services = Services.objects.select_related('owner', 'service').filter(owner=profile)
        
    services = Service.objects.filter(category__in=cats).order_by('category', 'name')
    data_dict = defaultdict(list)

    for service in services:
        data_dict[service.category].append(service)
    
    user_settings = profile.settings
    
    context = {
        'page_title': 'Edit Services - Torn Exchange',
        'categories': cats,
        'data_dict': data_dict,
        'owner_profile': profile,
        'user_services': user_services,
        'user_settings': user_settings,
    }
    
    if request.method == 'POST':
        updated_prices = {}
        all_services = Service.objects.all()
        
        for service in all_services:
            # monetary value of a service
            money_price = request.POST.get(f'{service.name}_money_price').strip()
            if money_price and money_price.strip():
                money_price = re.sub(r'[$,]', '', money_price)
            
            try:
                money_price = int(money_price)
            except Exception as e:
                money_price = 0
                
            # service value expressed in Torn items (like "1 xanax")
            barter_price = request.POST.get(f'{service.name}_barter_price').strip()
            barter_price = escape(barter_price) if barter_price else ''
            
            desc = request.POST.get(f'{service.name}_offer_description').strip()
            desc = escape(desc) if desc else ''
            
            if(money_price != 0 or barter_price != '' or desc != ''):
                updated_prices.update({service: {
                    'money_price': money_price,
                    'barter_price': barter_price,
                    'desc': desc,
                }})
                
        # delete all items first
        [a.delete() for a in Services.objects.filter(owner=profile)]
        
        # then recreate them again
        for key in updated_prices:
            service = updated_prices.get(key)
            
            Services.objects.update_or_create(
                owner=profile,
                service=key,
                defaults={
                    'money_price': service['money_price'],
                    'barter_price': service['barter_price'],
                    'offer_description': service['desc']
                })
            
        for service in all_services:
            checkbox_output = request.POST.get(f'{service}_checkbox')
            if checkbox_output == 'on':
                try:
                    Services.objects.get(owner=profile, service=service).delete()
                except:
                    pass
    
    return render(request, 'main/edit_services.html', context)


def services_list(request, identifier=None):
    if identifier is None:
        if request.user.is_authenticated:
            profile = (
                Profile.objects.filter(user=request.user)
                .order_by('-created_at')
                .first()
            )
            
            if profile:
                return redirect(reverse('services_list', args=[profile.name]))
        
        messages.error(request, 'You first need to log in to view your price list')
        return redirect('login')

    if request.user.is_authenticated:
        profile = (
            Profile.objects.filter(user=request.user)
            .order_by('-created_at')
            .first()
        )
        
        if profile:
            user_settings = Settings.objects.filter(owner=profile).get()
        else:
            user_settings = None
    else:
        profile = None
        user_settings = None

    # if the torn_id for the page corresponds to an existing profile
    if Profile.objects.filter(torn_id=identifier).exists():
        # Fetch the most recent profile with the matching torn_id
        pricelist_profile = (
            Profile.objects.filter(torn_id=identifier)
            .order_by('-created_at')
            .first()
        )
    elif Profile.objects.filter(name__iexact=identifier).exists():
        # Fetch the most recent profile with the matching name
        pricelist_profile = (
            Profile.objects.filter(name__iexact=identifier)
            .order_by('-created_at')
            .first()
        )
    else:
        context = {
            'error_message': f'Oops, looks like {identifier} does not correspond to a valid service list! Try checking the spelling for any typos.'
        }
        return render(request, 'main/error.html', context)
    
    owner_services = Services.objects.filter(
        owner=pricelist_profile).all()
    
    distinct_categories = set()
    for service in owner_services:
        distinct_categories.add(service.service.category)
        
    owner_settings = Settings.objects.filter(owner=pricelist_profile).get()
    vote_score = pricelist_profile.vote_score
    vote_count = pricelist_profile.votes.count()

    # Convert the set to a list if needed
    distinct_categories = list(distinct_categories)
    
    if owner_settings.service_list_description:
        description = owner_settings.service_list_description
    else:
        description = 'Welcome to '+pricelist_profile.name+'\'s price list for custom services.'
    
    context = {
        'page_type': 'service',
        'page_title': pricelist_profile.name+'\'s Custom Services - Torn Exchange',
        'content_title': pricelist_profile.name+'\'s Custom Services',
        'description': description,
        'services': owner_services,
        'distinct_categories': distinct_categories,
        'owner_profile': pricelist_profile,
        'user_profile': profile,
        'vote_score': vote_score,
        'vote_count': vote_count,
        'user_settings': user_settings,
        'owner_settings': owner_settings,
    }
    return render(request, 'main/services_list.html', context)


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


@login_required
def analytics(request):
    profile = Profile.objects.filter(user=request.user).get()
    context = return_profile_stats(profile)
    try:
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        user_settings = None
    
    if len(context['sellers']) > 0:
        # Extract the first 10 items from the dictionary
        first_10_sellers = dict(islice(context['sellers'].items(), 10))
        first_30_receipts = context['receipts'][:30]
    else:
        first_10_sellers = {}
        first_30_receipts = {}
        
    context.update({
        'user_settings': user_settings,
        'sellers': first_10_sellers,
        'receipts': first_30_receipts,
    })

    return render(request, 'main/analytics.html', context)


@login_required
def all_sellers(request: HttpRequest):
    profile = Profile.objects.filter(user=request.user).get()
    order_by = request.GET.get('order_by')
    
    # TODO: not supporting ordering by profit atm but maybe in the future
    if order_by == "profit":
        storage = messages.get_messages(request)
        storage.used = False
        messages.error(request, 'Ordering by profit is not yet supported')
        order_by = "seller"
        
    context = return_profile_stats(profile)
    try:
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        user_settings = None
        
    # set pagination for sellers
    sellers = list(context["sellers"].items())
    paginator = Paginator(sellers, 50)
    page = request.GET.get('page')
    results = paginator.get_page(page)
    converted_results = dict(results.object_list)
        
    context.update({
        'page_title': 'List of all sellers - Torn Exchange', 
        'user_settings': user_settings,
        'sellers': converted_results,
        'listings': results # for pagination
    })
    
    return render(request, 'main/all_sellers.html', context)


@login_required
def all_trades(request):
    profile = Profile.objects.filter(user=request.user).get()
    context = return_profile_stats(profile)
    try:
        user_settings = Settings.objects.filter(owner=profile).get()
    except:
        user_settings = None
        
    # set pagination for trades
    paginator = Paginator(context["receipts"], 50)
    page = request.GET.get('page')
    results = paginator.get_page(page)
        
    context.update({
        'user_settings': user_settings,
        'receipts': results,
        'listings': results # for pagination
    })
    
    return render(request, 'main/all_receipts.html', context)


@csrf_protect
def vote_view(request):
    if request.is_ajax and request.method == "POST":
        if request.user.is_authenticated == False:
            return JsonResponse({
                "error": "User not logged in",
            }, status=401)
        
        profile_name = request.POST.get('owner_username')
        voter_name = request.POST.get('voter_username')
        
        if profile_name == voter_name:
            return JsonResponse({
                "error": "You can't vote for yourself",
            }, status=400)
    
        profile = (
            Profile.objects.filter(name=profile_name)
            .order_by('-created_at')
            .first()
        )
        
        voter = (
            Profile.objects.filter(name=voter_name)
            .order_by('-created_at')
            .first()
        )
        voter_id = voter.id
        
        try:
            # Use the logged-in user as the voter
            voter = request.user.profile  # Assuming a one-to-one relationship between User and Profile
        except AttributeError:
            return JsonResponse({
                "error": "User does not have an associated profile.",
            }, status=400)
        
        if(request.user.profile.torn_id != voter.torn_id):
            return JsonResponse({
                "error": "Authenticated user mismatch",
            }, status=400)
        
        if voter_id is None:
            return JsonResponse({
                "error": "User not logged in",
            }, status=401)
        
        profile_id = profile.id
        direction = request.POST.get('direction')
        
        vote_count = profile.votes.count()
        vote_score = profile.vote_score

        direction_to_action = {'up': 0, 'down': 1}
        if profile.votes.exists(voter_id):
            previous_vote = Vote.objects.filter(user_id=voter_id, object_id=profile_id).get()
            if previous_vote.action == direction_to_action[direction]:
                return JsonResponse({
                    "error": "You already voted",
                }, status=400)
            else:
                if direction == 'up':
                    profile.votes.up(voter_id)
                elif direction == 'down':
                    profile.votes.down(voter_id)
        else:
            if direction == 'up':
                profile.votes.up(voter_id)
            elif direction == 'down':
                profile.votes.down(voter_id)
                
        vote_count = profile.votes.count()
        vote_score = profile.vote_score
        
        return JsonResponse({
            "vote_count": vote_count,
            "vote_score": vote_score,
        }, status=200)

    return JsonResponse({
        "error": "POST request is required for this action.",
    }, status=400)


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


def extension_get_prices(request):
    if request.is_ajax and request.method == "POST":
        try:
            userid = request.POST.get('user_id')
            seller_name = request.POST.get('seller_name')
            seller_name = re.sub('<div.*', '', seller_name)
            profile = Profile.objects.filter(user__username=userid).get()
            items = json.loads(request.POST.get('items'))
            items = [re.sub('<span.*', '', item).replace('\n',
                                                         '').replace('&amp;', "&") for item in items]
            
            quantities = json.loads(request.POST.get('quantities'))
            
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
            return JsonResponse({}, status=400)

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
        # print(data)
        return JsonResponse(data, status=200)

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


def create_receipt(request):
    if request.method == "POST":
        item_names = json.loads(request.POST.get('item_names'))
        item_names = [a[0].replace("&amp;", "&") for a in item_names]
        
        item_quantities = json.loads(request.POST.get('item_quantities'))
        item_quantities = [a[0] for a in item_quantities]
        
        item_prices = json.loads(request.POST.get('item_prices'))
        item_prices = [a[0] for a in item_prices]
        
        try:
            owner_name = request.POST.get('owner_username').strip('"')
        except:
            owner_user_id = request.POST.get('owner_user_id').strip('"')
            owner_name = None
            
        seller_name = request.POST.get('seller_username').strip('"')
        seller_name = re.sub('<div.*', '', seller_name)
        
        try:
            owner_profile = (
                Profile.objects.filter(name=owner_name)
                .order_by('-created_at')
                .first()
            )
        except:
            owner_profile = Profile.objects.filter(
            user__username=owner_user_id).get()
            
        trade_receipt = TradeReceipt(owner=owner_profile, seller=seller_name)
        trade_receipt.save()

        for i in range(len(item_names)):
            quantity = item_quantities[i]
            price = item_prices[i]
            item = Item.objects.filter(name=item_names[i]).get()
            item_trade = ItemTrade(
                owner=owner_profile, item=item, price=price, quantity=quantity, seller=seller_name
            )
            
            if item_trade.is_valid() == 'valid':
                item_trade.save()
                trade_receipt.items_trades.add(item_trade)
            else:
                return JsonResponse({'error_message': item_trade.is_valid()}, status=400)
        
        trade_receipt.save()
    
    ## CREATE CUSTOM MESSAGE
    
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

    return JsonResponse({
        'seller': seller_name,
        'receipt_id': trade_receipt.receipt_url_string,
        'trade_message': escape(trade_paste_text),
        'profit': trade_receipt.profit,
        'total': trade_receipt.total,
    }, status=200)


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


def delete_receipt_from_profile(request, receipt_id):
    if request.method == 'POST':
        trade_receipt = TradeReceipt.objects.filter(id=receipt_id).get()
        trade_items = trade_receipt.items_trades.all()
        [a.delete() for a in trade_items]
        trade_receipt.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'analytics'))


def museum_helper(request):
    context = {
        'page_title': 'Zim\'s Museum Helper - Torn Exchange',
    }
    
    return render(request, 'main/museum_helper.html', context)


def custom_csrf_failure_view(request, reason=""):
    """
    Handles CSRF failures and returns an appropriate JSON response for APIs.
    """
    if request.content_type == "application/json":
        return JsonResponse(
            {"error": "CSRF token missing or incorrect.", "details": reason},
            status=403,
        )
    else:
        return JsonResponse(
            {"error": "Invalid request. Ensure the CSRF token is included."},
            status=403,
        )


def custom_404(request, invalid_path=None):
    context = {
        'error_message': 'Page not found'
    }
    return render(request, 'main/error.html', context, status=404)


def render_static(request, file):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'static', 'main' ,file)
    with open(file_path, 'r') as file:
        return HttpResponse(file.read(), content_type='text/plain')


def tutorial(request):
    data = cache.get("tutorial_data")
    if data:
        html_content = data
    else:
        api_url = "https://api.torn.com/v2/forum/16447032/thread"
        headers = {
            "Authorization": "ApiKey " + os.getenv("SYSTEM_API_KEY")
        }
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            html_content = data.get("thread", {}).get("content_raw", "<p>No content available.</p>")
            
            cache.set("tutorial_data", html_content, 60*60*24)
        else:
            html_content = "<p>Failed to fetch data.</p>"
        
    context = {
        'page_title': 'Torn Exchange Tutorial',
        'html_content': html_content
    }
    
    link = '<a href="https://www.torn.com/forums.php#/p=threads&f=61&t=16447032&b=0&a=0" target="_blank">here</a>'
    messages.info(request, 
        mark_safe(f'<b>Note</b>: This page is automatically updated from original tutorial that can be found on Torn forum {link}.')
        )

    return render(request, "main/tutorial.html", context)


@login_required
def manage_price_list(request):
    cats = categories()
    
    profile = (
        Profile.objects.select_related('settings')
        .filter(user_id=request.user.profile.user_id)
        .order_by('-created_at')
        .first()
    )

    if profile.order_categories:
        cats = profile.order_categories
    
    context = {
        'page_title': 'Manage Price List - Torn Exchange',
        'hidden_categories': profile.hidden_categories,
        'categories': cats,
        'owner_profile': profile,
    }
    
    return render(request, 'main/manage_price_list.html', context)


@login_required
@csrf_exempt
@require_POST
def toggle_category_visibility(request):
    data = json.loads(request.body)
    category = data.get('category')
    is_checked = data.get('is_checked')
    profile = request.user.profile

    # checked means it is NOT hidden
    if is_checked:
        if category in profile.hidden_categories:
            del profile.hidden_categories[category]
    else:
        profile.hidden_categories[category] = True

    profile.save()
    return JsonResponse({'success': True})


@login_required
@csrf_exempt
@require_POST
def save_category_order(request):
    data = json.loads(request.body)
    order = data.get('order')
    profile = request.user.profile

    profile.order_categories = order
    profile.save()
    return JsonResponse({'success': True})


def sitemap(request):
    links = [
        {
            'category': 'Main',
            'urls': [
                {'name': 'Home', 'url': reverse('home')},
                {'name': 'About', 'url': reverse('about')},
            ]
        },
        {
            'category': 'Listings',
            'urls': [
                {'name': 'Search for Best Deals', 'url': reverse('listings')},
                {'name': 'Search Custom Services', 'url': reverse('search_services')},
                {'name': 'Job Seekers', 'url': reverse('employee_listings')},
                {'name': 'Revivers', 'url': reverse('revives_listings')},
                {'name': 'Loss Sellers', 'url': reverse('losses_listings')},
                {'name': 'Companies for Sale', 'url': reverse('company_listings')},
                {'name': 'Companies Hiring', 'url': reverse('companies_hiring')},
                {'name': 'Museum Helper', 'url': reverse('museum_helper')},
            ]
        },
        {
            'category': 'User Services',
            'urls': [
                {'name': 'My Price List', 'url': reverse('price_list')},
                {'name': 'Edit Price List', 'url': reverse('edit_price_list')},
                {'name': 'Manage Price List', 'url': reverse('manage_price_list')},
                {'name': 'My Services', 'url': reverse('services_list')},
                {'name': 'Edit Services', 'url': reverse('edit_services')},
            ]
        },
        {
            'category': 'Tools',
            'urls': [
                {'name': 'Calculator', 'url': reverse('calculator')},
                {'name': 'Analytics', 'url': reverse('analytics')},
                {'name': 'Settings', 'url': reverse('settings')},
                {'name': 'API Documentation', 'url': reverse('api_home')},
                {'name': 'Tutorial', 'url': reverse('forum_tutorial')},
            ]
        },
    ]
    return render(request, 'main/sitemap.html', {'links': links})
