from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpRequest, HttpResponseNotFound, JsonResponse
from django.contrib import messages
from django.conf import settings as project_settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt

from main.model_utils import get_all_time_leaderboard, get_active_traders, get_most_trades, get_changelog
from .models import Item, Listing, Service, Services, TradeReceipt, ItemTrade, Company
from .filters import ListingFilter, EmployeeListingFilter, CompanyListingFilter, ServicesFilter
from users.models import Profile, Settings
from users.forms import SettingsForm
from django.core.paginator import Paginator
import re
import json
from django.db.models import F
from .profile_stats import return_profile_stats


# Create your views here.
from vote.models import Vote
from hitcount.views import HitCountMixin
from hitcount.models import HitCount
from main.te_utils import categories, merge_items, parse_trade_text, return_item_sets, dictionary_of_categories, service_categories, get_services_view

from html import escape


def homepage(request):
    all_time_traders = get_all_time_leaderboard()
    active_traders = get_active_traders()
    most_receipts = get_most_trades()
    created_today, changes_this_week, changes_this_month = get_changelog()
    
    try:
        profile = Profile.objects.filter(user=request.user).get()
        user_settings = Settings.objects.filter(owner=profile).get()
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
    queryset = Listing.objects.all().order_by('-last_updated')
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
        print(e)
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
        print(e)
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
    profile = Profile.objects.filter(user=request.user).get()
    
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

    user_settings = Settings.objects.filter(owner=profile).get()
    
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
    if identifier is None:
        try:
            profile = Profile.objects.filter(user=request.user).get()
            return redirect(reverse('price_list', args=[profile.name]))
        except:
            return (redirect(f'login'))

    # if the torn_id for the page corresponds to an existing profile
    if Profile.objects.filter(torn_id=identifier).exists():
        try:
            # fetches the profile of the visiting user
            profile = Profile.objects.filter(user=request.user).get()
        except:
            profile = None
            
        # fetches the profile of the pricelist owner
        pricelist_profile = Profile.objects.filter(torn_id=identifier).get()

    # fetches the profile of the visiting user using profile name
    elif Profile.objects.filter(name__iexact=identifier).exists():
        try:
            profile = Profile.objects.filter(user=request.user).get()
        except:
            profile = None
        pricelist_profile = Profile.objects.filter(name__iexact=identifier).get()

    else:
        return HttpResponseNotFound(f'Oops, looks like {identifier} does not correspond to a valid pricelist! Try checking the spelling for any typos.')


    # COUNTING HITS

    hit_count = HitCount.objects.get_for_object(pricelist_profile)
    hit_count_response = HitCountMixin.hit_count(request, hit_count)

    #####
    
    listings = Listing.objects.filter(
        owner=pricelist_profile).all().order_by('-item__TE_value')
    
    try:
        last_updated = listings.order_by(
            '-item__last_updated').first().item.last_updated
    except AttributeError:
        last_updated = None
    
    all_relevant_items = Listing.objects.filter(owner=pricelist_profile).select_related('item').order_by('-item__TE_value')
    
    distinct_categories = [a['item__item_type'] for a in all_relevant_items.values('item__item_type').distinct()]
    
    item_types = [x for x in categories() if (x in distinct_categories)]

    if profile:
        user_settings = Settings.objects.filter(owner=profile).get()
    else:
        user_settings = None
        
    owner_settings = Settings.objects.filter(owner=pricelist_profile).get()
    vote_score = pricelist_profile.vote_score
    vote_count = pricelist_profile.votes.count()
    
    last_receipt = TradeReceipt.objects.filter(owner=pricelist_profile).last()
    time_since_last_trade = getattr(last_receipt, "created_at", None)
    
    context = {
        'page_title': pricelist_profile.name+'\'s Price List - Torn Exchange',
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
    
    data_dict = {}
    cats = service_categories()
    user_services = Services.objects.filter(owner=profile)
        
    for category in cats:
        data_dict.update({category: Service.objects.filter(
            category=category).order_by('name')
        })
    
    user_settings = Settings.objects.filter(owner=profile).get()
    
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
        try:
            profile = Profile.objects.filter(user=request.user).get()
            return redirect(reverse('services_list', args=[profile.name]))
        except:
            return (redirect(f'login'))

    # if the torn_id for the page corresponds to an existing profile
    if Profile.objects.filter(torn_id=identifier).exists():
        try:
            # fetches the profile of the visiting user
            profile = Profile.objects.filter(user=request.user).get()
        except:
            profile = None
        # fetches the profile of the pricelist owner
        pricelist_profile = Profile.objects.filter(torn_id=identifier).get()

    # fetches the profile of the visiting user using profile name
    elif Profile.objects.filter(name__iexact=identifier).exists():
        try:
            profile = Profile.objects.filter(user=request.user).get()
        except:
            profile = None
        pricelist_profile = Profile.objects.filter(name__iexact=identifier).get()

    else:
        return HttpResponseNotFound(f'Oops, looks like {identifier} does not correspond to a valid pricelist! Try checking the spelling for any typos.')

    if profile:
        user_settings = Settings.objects.filter(owner=profile).get()
    else:
        user_settings = None
    
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
    
    context = {
        'page_title': pricelist_profile.name+'\'s Custom Services - Torn Exchange',
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
    listings = Listing.objects.filter(owner=profile).all()
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
        
    context.update({'user_settings': user_settings})

    return render(request, 'main/analytics.html', context)


@login_required
def vote_view(request):
    if request.is_ajax and request.method == "POST":
        profile_name = request.POST.get('owner_username')
        voter_name = request.POST.get('voter_username')
        profile = Profile.objects.filter(name=profile_name).get()
        voter_id = Profile.objects.filter(name=voter_name).get().id
        if voter_id is None:
            return redirect('login')
        profile_id = profile.id
        direction = request.POST.get('direction')

        direction_to_action = {'up': 0, 'down': 1}
        if profile.votes.exists(voter_id):
            previous_vote = Vote.objects.filter(
                user_id=voter_id, object_id=profile_id).get()
            if previous_vote.action == direction_to_action[direction]:
                pass
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


def parse_trade_paste(request):
    if request.method == "POST":
        username = request.POST.get('profile')
        profile = Profile.objects.filter(name=username).get()
        trade_paste = (request.POST.get('prompt', None))

        if trade_paste is not None:
            name, item_list, item_quantities = parse_trade_text(trade_paste)

            item_list, item_quantities = return_item_sets(
                item_list, item_quantities)

            price_list = [buy_price_from_name(a, profile) for a in item_list]
            item_urls = [Item.objects.filter(
                name=a).get().image_url for a in item_list]
            market_prices = [Item.objects.filter(
                name=a).get().TE_value for a in item_list]

            item_list = [escape(a) for a in item_list]
            name = escape(name)

            return JsonResponse({"name": name, "items": item_list, "qty": item_quantities, "price": price_list, 'market_prices': market_prices, 'img_url': item_urls}, status=200)

    return JsonResponse({}, status=400)


@csrf_exempt
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
                    print(e)
                    profit_per_item.append(0)
            image_url = [
                a.image_url if a is not None else '' for a in items_objects]
            market_values = [
                a.TE_value if a is not None else 0 for a in items_objects]
        except Exception as e:
            print(e)
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
            profile = Profile.objects.filter(name__iexact=user_name).get()
            items = data.get('items')
            quantities = data.get('quantities')
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
                    print(e)
                    profit_per_item.append(0)
            image_url = [
                a.image_url if a is not None else '' for a in items_objects]
            market_values = [
                a.TE_value if a is not None else 0 for a in items_objects]
        
        except Exception as e:
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
def create_receipt(request):
    if request.method == "POST":
        item_names = json.loads(request.POST.get('item_names'))
        print(item_names)
        item_names = [a[0].replace("&amp;", "&") for a in item_names]
        print(item_names)
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
            owner_profile = Profile.objects.filter(name=owner_name).get()
        except:
            owner_profile = Profile.objects.filter(
                user__username=owner_user_id).get()
        trade_receipt = TradeReceipt(owner=owner_profile, seller=seller_name)
        trade_receipt.save()

        for i in range(len(item_names)):
            quantity = item_quantities[i]
            price = item_prices[i]
            # print(item_names[i], quantity, price)
            item = Item.objects.filter(name=item_names[i]).get()
            # print(f'item trade added with {item},{quantity},{price}')
            item_trade = ItemTrade(
                owner=owner_profile, item=item, price=price, quantity=quantity, seller=seller_name)
            # print(item_trade.is_valid())
            if item_trade.is_valid() == 'valid':
                item_trade.save()
                trade_receipt.items_trades.add(item_trade)
            else:
                return JsonResponse({'error_message': item_trade.is_valid()}, status=400)
        trade_receipt.save()
        # print('receipt has been saved')
    return JsonResponse({'receipt_id': trade_receipt.receipt_url_string}, status=200)


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
            owner=owner_profile, seller=seller_name).count()
            trade_paste_text = owner_profile.settings.receipt_paste_text

            # error handling for when trader hasn't yet set any message in Settings:
            trade_paste_text = '' if trade_paste_text is None else trade_paste_text

            trade_paste_text = trade_paste_text.replace(
                '[[seller_name]]', seller_name)
            trade_paste_text = trade_paste_text.replace(
                '[[total]]', "${:,.0f}".format(trade_receipt.total))
            trade_paste_text = trade_paste_text.replace(
                '[[receipt_link]]', f'www.tornexchange.com/receipt/{trade_receipt.receipt_url_string}')
            trade_paste_text = trade_paste_text.replace(
                '[[trade_number]]', str(listings_count))
            trade_paste_text = trade_paste_text.replace(
                '[[prices_link]]', f'www.tornexchange.com/prices/{owner_profile.name}')
            trade_paste_text = trade_paste_text.replace(
                '[[forum_link]]', f'www.torn.com/{owner_profile.settings.link_to_forum_post}')
            
            data = {'receipt_id': trade_receipt.receipt_url_string,
                    'trade_message': escape(trade_paste_text),
                    'profit': trade_receipt.profit,
                    'total': trade_receipt.total,
                    }
            
        except Exception as e:
            print(e)
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


def buy_price_from_name(item_name, profile):
    try:
        item = Item.objects.get(name=item_name)
    except Item.DoesNotExist:
        print(f"Item with name '{item_name}' does not exist.")
        return 0

    try:
        listing = Listing.objects.get(owner=profile, item=item)
        return listing.effective_price
    except Listing.DoesNotExist:
        print(f"Listing for item '{item_name}' does not exist for the specified profile.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return 0


def delete_receipt_from_profile(request, receipt_id):
    if request.method == 'POST':
        trade_receipt = TradeReceipt.objects.filter(id=receipt_id).get()
        trade_items = trade_receipt.items_trades.all()
        [a.delete() for a in trade_items]
        trade_receipt.delete()
    return redirect('analytics')


def museum_helper(request):
    context = {
        'page_title': 'Zim\'s Museum Helper - Torn Exchange',
    }
    
    return render(request, 'main/museum_helper.html', context)
