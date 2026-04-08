import csv
import json
import os
import time
from functools import wraps
from typing import List

from django.core.cache import cache

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import OuterRef, Q, Subquery

from main.filters import ListingFilter
from main.profile_stats import return_profile_stats
from .models import Item, Listing, Profile, TradeReceipt
from main.te_utils import (get_ordered_categories)


# This variable should make typing faster
ce = csrf_exempt

"""
The idea here is that /api will respond with a html page and then all the endpoints
will fall under /api/endpoint

so I will start of with a /api/test endpoint that will respond with json output of the api status

"""

### HELPER FUNCTIONS ###

def export_to_csv(data, filename):
    """
    Exports data to CSV format.
    
    :param data: List of dictionaries containing the data to be exported.
    :param filename: The name of the file to be exported.
    :return: HttpResponse with CSV data.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    
    if data:
        # Write headers
        writer.writerow(data[0].keys())
        
        # Write data rows
        for row in data:
            writer.writerow(row.values())

    return response


def rate_limit_exponential(view_func):
    @wraps(view_func)
    def _wrapped_throttle(request, *args, **kwargs):
        ip = get_client_ip(request)
        window_key = f"rate_limit:window:{ip}"
        penalty_key = f"rate_limit:penalty:{ip}"
        now = time.time()

        penalty = cache.get(penalty_key, {"attempts": 0, "next_time": 0})
        if now < penalty["next_time"]:
            wait = int(penalty["next_time"] - now)
            return JsonResponse({
                "status": "error",
                "rate_limited": True,
                "retry_after": wait
            }, status=429)

        window = cache.get(window_key, [])
        window = [ts for ts in window if now - ts < 60]

        if len(window) >= 10:
            penalty["attempts"] += 1
            wait_time = min(15 * (2 ** (penalty["attempts"] - 1)), 172800)
            penalty["next_time"] = now + wait_time
            cache.set(penalty_key, penalty, timeout=172800)
            return JsonResponse({
                "status": "error",
                "rate_limited": True,
                "retry_after": int(wait_time)
            }, status=429)

        window.append(now)
        cache.set(window_key, window, timeout=60)
        return view_func(request, *args, **kwargs)

    return _wrapped_throttle


def get_client_ip(request):
    return (
        request.META.get("HTTP_X_FORWARDED_FOR")
        or request.META.get("CF_CONNECTING_IP")
        or request.META.get("CF_CONNECTING_IPV6")
        or request.META.get("REMOTE_ADDR")
    )


@ce
@rate_limit_exponential
def api_404(request, invalid_path=None):
    return JsonResponse({"status": "error", "message": "Endpoint not found"}, status=404)


def js(data, meta=None):
    if(meta):
        return JsonResponse({"status": "success", "meta": meta, "data": data})
    return JsonResponse({"status": "success", "data": data})


def je(message):
    return JsonResponse({"status": "error", "message": message}, status=400)


def require_api_key(view_func):
    """Authenticate requests via ?key= parameter matched against Profile.api_key."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        key = request.GET.get('key') or (
            json.loads(request.body).get('key')
            if request.content_type == 'application/json' and request.body
            else None
        )
        if not key:
            return JsonResponse({"status": "error", "message": "Missing API key"}, status=401)
        try:
            profile = Profile.objects.get(api_key=key)
        except Profile.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Invalid API key"}, status=401)
        request.api_profile = profile
        return view_func(request, *args, **kwargs)
    return _wrapped


### API functions ###

@ce
def swag_yaml(request):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'swagger.yaml')

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return HttpResponse(file_content, content_type='text/plain')
    except Exception as e:
        return HttpResponse(f"Error: {type(e).__name__}: {e}", status=500)


def api_home(request):
    return render(request, 'swagger.html')


@ce
@rate_limit_exponential
def test(request):
    if request.method == 'GET':
        try:
            result = "API is working"
            return js("success", result)
        except json.JSONDecodeError:
            return je("Invalid JSON")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def price(request):
    # Example usage: /api/price?item_id=<ITEM_ID>&user_id=<USER_ID>&key=<KEY>
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            item_id = request.GET.get('item_id')

            cache_key = f'api_price_{user_id}_{item_id}'
            cached = cache.get(cache_key)
            if cached:
                return JsonResponse(cached)

            profile = get_object_or_404(Profile, torn_id=user_id)
            item = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()

            if not item:
                return je("Item does not exist in TE DB. Check item's circulation number.")

            listing = Listing.objects.filter(owner=profile, item=item).first()

            if listing:
                data = {
                    "status": "success",
                    "data": {
                        "trader": listing.owner.name,
                        "price": listing.effective_price,
                        "item": listing.item.name
                    }
                }
                cache.set(cache_key, data, timeout=300)
                return JsonResponse(data)
            else:
                return je("Listing not found")
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def profile(request):
    """
    Example URL usage:
    /api/profile?user_id=<USER_ID>&key=<KEY>
    """
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')

            cache_key = f'api_profile_{user_id}'
            cached = cache.get(cache_key)
            if cached:
                return JsonResponse(cached)

            p = Profile.objects.select_related('settings').filter(torn_id=user_id).get()

            data = {
                "status": "success",
                "data": {
                    "name": p.name,
                    "torn_id": p.torn_id,
                    "activity_status": p.activity_status,
                    "last_active": p.last_active,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "votes": p.vote_score,
                    "reviews": p.settings.link_to_forum_post,
                }
            }
            cache.set(cache_key, data, timeout=300)
            return JsonResponse(data)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
def TE_price(request):
    # Gets the TE MV from the database and compares it to torn MV
    # Example URL usage: /api/TE_price?item_id=<ITEM_ID>&key=<KEY>
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')

            cache_key = f'api_TE_price_{item_id}'
            cached = cache.get(cache_key)
            if cached:
                return js(cached)

            item = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()

            if not item:
                return je("Item does not exist in TE DB. Check item's circulation number.")

            data = {
                "item": item.name,
                "te_price": item.TE_value,
                "torn_price": item.market_value
            }
            cache.set(cache_key, data, timeout=300)
            return js(data)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def allTE_prices(request):
    if request.method == 'GET':
        try:
            cache_key = 'allTE_prices_data'
            data = cache.get(cache_key)

            if data is None:
                items = Item.objects.all().order_by('item_id')
                data = [
                    {
                        "item_id": item.item_id,
                        "item_name": item.name,
                        "te_price": item.TE_value,
                        "torn_price": item.market_value
                    }
                    for item in items
                ]

                # Cache for 5 minutes (300 seconds)
                cache.set(cache_key, data, timeout=300)

            return js(data)
        except Exception as E:
            return je("Invalid request parameters")


@ce
@rate_limit_exponential
@require_api_key
def listings(request):
    """
    Example URL usage: /api/get_prices?item_id=<ITEM_ID>&sort_by=<SORT_BY>&order=<ORDER>&page=1&key=<KEY>
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            sort_by = request.GET.get('sort_by', 'price').lower()
            order = request.GET.get('order', 'asc').lower()
            page = request.GET.get('page', '1')

            cache_key = f'api_listings_{item_id}_{sort_by}_{order}_{page}'
            cached = cache.get(cache_key)
            if cached:
                return JsonResponse(cached)

            item = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()
            
            if not item:
                return je("Item does not exist in TE DB. Check item's circulation number.")
            
            queryset = Listing.objects.filter(item=item, hidden=False).select_related('owner', 'item')

            # map 'price' to 'effective_price' for backward compatibility
            if sort_by == 'price':
                sort_by = 'effective_price'

            valid_sort_fields = ['effective_price']
            if sort_by not in valid_sort_fields:
                return je("Invalid sort field")

            if order == 'desc':
                sort_by = f'-{sort_by}'

            myFilter = ListingFilter(request.GET, queryset=queryset)
            filtered_listings = myFilter.qs
            filtered_listings = filtered_listings.exclude(effective_price__isnull=True)
            filtered_listings = filtered_listings.order_by(sort_by)

            # Handle pagination
            paginator = Paginator(filtered_listings, 20)
            try:
                paged_listings = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                paged_listings = paginator.page(1)

            data = {
                "status": "success",
                "data": {
                    "item": item.name,
                    "meta": {
                        "total_listings": paginator.count,
                        "total_pages": paginator.num_pages,
                        "current_page": paged_listings.number,
                    },
                    "listings": [
                        {
                            "trader": listing.owner.name,
                            "price": listing.effective_price,
                            "item": listing.item.name
                        } for listing in paged_listings
                    ]
                }
            }
            cache.set(cache_key, data, timeout=300)
            return JsonResponse(data)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
def best_listing(request):
    """
    Example URL usage: /api/best_listing?item_id=<ITEM_ID>&key=<KEY>
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')

            cache_key = f'api_best_listing_{item_id}'
            cached = cache.get(cache_key)
            if cached:
                return js(cached)

            item = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()

            if not item:
                return je("Item does not exist in TE DB. Check item's circulation number.")

            base_qs = Listing.objects.filter(item=item).select_related('owner', 'item').order_by('-last_updated')
            myFilter = ListingFilter(request.GET, queryset=base_qs)
            filtered = myFilter.qs

            filtered = (
                filtered
                .exclude(hidden=True)
                .exclude(effective_price__isnull=True)
                .filter(owner__active_trader=True)
            )

            candidates = filtered.order_by('-effective_price', '-last_updated')[:10]
            listing = next((l for l in candidates if l.owner.vote_score >= 0), None)

            if listing:
                data = {
                    "item": item.name,
                    "trader": listing.owner.name,
                    "trader_id": listing.owner.torn_id,
                    "vote": listing.owner.vote_score,
                    "price": listing.effective_price,
                    "te_price": item.TE_value,
                    "torn_mv": item.market_value,
                }
                cache.set(cache_key, data, timeout=300)
                return js(data)
            else:
                return je("No listings found for the specified item")

        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def receipts(request):
    """Get all receipts for a user

    Args:
        request (HttpRequest): HttpRequest object

    Returns:
        JSON: structured data of all receipts for a user
    """    
    if request.method == 'GET':
        try:
            output_format = request.GET.get('format')
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 100))

            profile = request.api_profile
            receipts = TradeReceipt.objects.filter(owner=profile).all().order_by('-created_at')
            
            paginator = Paginator(receipts, per_page)
            try:
                paged_receipts = paginator.page(page)
            except PageNotAnInteger:
                paged_receipts = paginator.page(1)
            except EmptyPage:
                paged_receipts = paginator.page(paginator.num_pages)
            
            data = [
                {
                    "created_at": receipt.created_at,
                    "seller": receipt.seller,
                    "total": receipt.total,
                    "profit": receipt.profit,
                    "url": f'https://tornexchange.com/receipt/{receipt.receipt_url_string}',
                }
                for receipt in paged_receipts
            ]
            
            if output_format == "csv":
                return export_to_csv(data, 'receipts')
            
            meta = {
                "count": receipts.count(),
                "page": page,
                "per_page": per_page,
                "total_pages": paginator.num_pages,
            }
            
            return js(data, meta)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
def receipt(request, receipt_id=None):
    try:
        receipt = get_object_or_404(TradeReceipt, receipt_url_string=receipt_id)
        items_trades = receipt.items_trades.select_related('item').all()
        meta = {
            "receipt_id": receipt.receipt_url_string,
            "created_at": receipt.created_at,
            "seller": receipt.seller,
            "total": receipt.total,
            "profit": receipt.profit,
        }
        data = {
            item_trade.item.item_id: {
                "name": item_trade.item.name,
                "price": item_trade.price,
                "quantity": item_trade.quantity,
                "subtotal": item_trade.sub_total,
            }
            for item_trade in items_trades
        }
        return js(data, meta)
    except Exception as E:
        return je('Page not found, wrong Receipt ID in the URL')


@ce
@rate_limit_exponential
@require_api_key
def sellers(request):
    """Get all sellers (customers) for a user

    Args:
        request (HTTPRequest): HTTPRequest object

    Returns:
        JSON: structured data of all sellers for a user
    """    
    if request.method == 'GET':
        try:
            outputFormat = request.GET.get('format')

            profile = request.api_profile
            raw_data = return_profile_stats(profile)
            
            sellers = raw_data['sellers']
            profits = raw_data['top_profits']
            
            data = [{
                "name": name,
                "trades": int(item['trade_count']),
                "profit": int(profits.get(name, 0)),
                "last_traded": str(item['last_traded']),
                }
                for name, item in sellers.items()
            ]
            
            if outputFormat == "csv":
                return export_to_csv(data, 'sellers')
            
            meta = {
                "count": len(sellers),
            }
            
            return js(data, meta)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def modify_listing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            global_action = data.get('action')
            listings_data = data.get('listings', [])

            if not listings_data:
                return je("Missing required parameters")

            profile = request.api_profile

            updated = []
            failed = []
            deleted = []

            for entry in listings_data:
                item_id = entry.get('item_id')
                action = entry.get('action', global_action)
                fixed_price = entry.get('fixed_price')
                discount = entry.get('discount')

                if not item_id or not action:
                    continue

                item = Item.objects.filter(item_id=item_id).order_by('-last_updated').first()
            
                if not item:
                    continue
                
                listing = Listing.objects.filter(owner=profile, item=item).first()

                if action == 'update':
                    try:
                        if fixed_price is not None:
                            fixed_price = int(fixed_price)
                        if discount is not None:
                            if discount < 1 or discount > 100:
                                failed.append(item_id)
                                continue

                        if fixed_price is None and discount is None:
                            failed.append(item_id)
                            continue

                        if not listing:
                            listing = Listing.objects.create(owner=profile, item=item)

                        listing.price = fixed_price if fixed_price is not None else None
                        listing.discount = float(discount) if discount is not None else None
                        listing.effective_price = listing.calculate_effective_price()
                        listing.save(update_fields=['price', 'discount', 'effective_price'])
                        updated.append(item_id)

                    except Exception as e:
                        failed.append(item_id)
                        continue

                elif action == 'delete':
                    if not listing:
                        continue

                    listing.delete()
                    deleted.append(item_id)

            return js({"updated_listings": updated, "failed_listings": failed, 'deleted_listings': deleted})

        except Exception as e:
            je(str(e))
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def active_traders(request):
    try:
        cache_key = 'api_active_traders'
        cached = cache.get(cache_key)
        if cached:
            return js(cached)

        last_receipt_qs = TradeReceipt.objects.filter(
            owner=OuterRef('pk')
        ).order_by('-created_at').values('created_at')[:1]

        traders = Profile.objects.filter(active_trader=True).annotate(
            last_receipt_at=Subquery(last_receipt_qs)
        )
        ids_only = []
        full_data = {}

        for trader in traders:
            ids_only.append(int(trader.torn_id))

            time_since_last_trade = int(trader.last_receipt_at.timestamp()) if trader.last_receipt_at else None

            full_data[trader.torn_id] = {
                "name": trader.name,
                "torn_id": int(trader.torn_id),
                "last_trade": time_since_last_trade
            }

        data = {
            "ids": ids_only,
            "verbose": full_data
        }
        cache.set(cache_key, data, timeout=300)
        return js(data)
    except Exception as e:
        print("Error fetching active traders:", e)
        return je("Error fetching active traders")


@ce
@rate_limit_exponential
@require_api_key
def price_list(request, identifier=None):
    """
    Example URL usage: /api/prices/<IDENTIFIER>
    """
    if request.method == 'GET':
        try:
            cache_key = f'api_price_list_{identifier}'
            cached = cache.get(cache_key)
            if cached:
                return JsonResponse(cached)

            pricelist_profile = (
                Profile.objects.select_related('settings')
                .filter(Q(torn_id=identifier) | Q(name__iexact=identifier))
                .order_by('-created_at')
                .first()
            )
            
            if pricelist_profile:
                owner_settings = pricelist_profile.settings
            else:
                message = f'Oops, looks like {identifier} does not correspond to a valid pricelist! Try checking the spelling for any typos.'
                return je(message=message)
            
            all_relevant_items = Listing.objects.filter(
                owner=pricelist_profile
            ).select_related('owner', 'item', 'owner__settings') \
            .exclude(price__isnull=True, discount__isnull=True) \
            .order_by('-item__TE_value')
            
            last_receipt = TradeReceipt.objects.select_related('owner').filter(owner=pricelist_profile).last()

            try:
                last_updated = all_relevant_items.order_by('-item__last_updated').first().item.last_updated
            except AttributeError:
                last_updated = None

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
                 
            # Serialize queryset to JSON-friendly structures
            items_serialized = []
            for listing in all_relevant_items:
                item = listing.item
                items_serialized.append({
                    "item_id": item.item_id,
                    "name": item.name,
                    "price": getattr(listing, "effective_price", None),
                }) if getattr(listing, "hidden", False) == False else None
                    
            data = {
                'items': items_serialized,
            }        
            
            meta = {
                'description': description,
                'trader': pricelist_profile.name,
                'vote_score': vote_score,
                'last_updated': last_updated.isoformat() if last_updated else None,
                'time_since_last_trade': time_since_last_trade.isoformat() if time_since_last_trade else None,
            }
            
            response_data = {"status": "success", "meta": meta, "data": data}
            cache.set(cache_key, response_data, timeout=300)
            return JsonResponse(response_data)
        except Exception as E:
            print("Error in price_list API:", E)
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
@rate_limit_exponential
@require_api_key
def all_best_listings(request):
    """
    Example URL usage: /api/all_best_listings
    Returns the 3 best traders (ordered by price) for each item.

    Filters:
    - Excludes hidden listings
    - Excludes listings with null effective_price
    - Only includes active traders
    - Excludes traders with negative vote_score
    """
    if request.method == 'GET':
        try:
            cache_key = 'api_all_best_listings'
            cached = cache.get(cache_key)
            if cached:
                return js(cached)

            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        i.item_id,
                        i.name        AS item_name,
                        p.name        AS trader_name,
                        p.torn_id      AS trader_id,
                        l.effective_price,
                        p.vote_score
                    FROM (
                        SELECT
                            l2.id,
                            ROW_NUMBER() OVER (
                                PARTITION BY l2.item_id
                                ORDER BY l2.effective_price DESC, l2.last_updated DESC
                            ) AS rn
                        FROM main_listing l2
                        INNER JOIN users_profile p2 ON p2.id = l2.owner_id
                        WHERE l2.hidden = FALSE
                          AND l2.effective_price IS NOT NULL
                          AND l2.effective_price <> 0
                          AND p2.active_trader = TRUE
                          AND p2.vote_score >= 0
                    ) ranked
                    INNER JOIN main_listing l  ON l.id  = ranked.id
                    INNER JOIN main_item    i  ON i.id  = l.item_id
                    INNER JOIN users_profile p ON p.id  = l.owner_id
                    WHERE ranked.rn <= 3
                    ORDER BY i.item_id, l.effective_price DESC
                """)
                rows = cursor.fetchall()

            data = {}
            for item_id, item_name, trader_name, trader_id, effective_price, vote_score in rows:
                key = str(item_id)
                if key not in data:
                    data[key] = {"item": item_name, "traders": []}
                data[key]["traders"].append({
                    "trader": trader_name,
                    "trader_id": trader_id,
                    "price": effective_price,
                    "vote_score": vote_score,
                })
            
            cache.set(cache_key, data, timeout=300)
            return js(data)
        except Exception as E:
            print("Error in all_best_listings API:", E)
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")
