import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Listing, Profile, Item

# This variable should make typing faster
ce = csrf_exempt

"""
The idea here is that /api will respond with a html page and then all the endpoints
will fall under /api/endpoint

so I will start of with a /api/test endpoint that will respond with json output of the api status

"""

def api_home(request):
    return render(request, 'main/api_home.html')


@ce
def test(request):
    if request.method == 'GET':
        try:
            result = "API is working"
            return JsonResponse({"status": "success", "result": result})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"})
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})


@ce
def price(request):
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            item_id = request.GET.get('item_id')

            profile = get_object_or_404(Profile, torn_id=user_id)
            item = get_object_or_404(Item, item_id=item_id)

            listing = Listing.objects.filter(owner=profile, item=item).first()

            if listing:
                return JsonResponse({
                    "status": "success",
                    "data": {
                        "trader": listing.owner.name,
                        "price": listing.effective_price,
                        "item": listing.item.name
                    }
                })
            else:
                return JsonResponse({"status": "error", "message": "Listing not found"})
        except Exception as E:
            return JsonResponse({
                "status": "error", 
                "message": "Invalid request parameters", 
                "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})

@ce
def get_profile_details(request):
    """
    Example URL usage:
    /api/get_profile_details?user_id=<USER_ID>
    """
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            profile = get_object_or_404(Profile, torn_id=user_id)

            return JsonResponse({
                "status": "success",
                "data": {
                    "name": profile.name,
                    "torn_id": profile.torn_id,
                    "activity_status": profile.activity_status,
                    "last_active": profile.last_active,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                }
            })
        except Exception as E:
            return JsonResponse({
                "status": "error",
                "message": "Invalid request parameters", 
                "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})


@ce
def TE_price(request):
    # Gets the TE MV from the database and compares it to torn MV
    # ExAmple URL usage: /api/TE_price?item_id=<ITEM_ID>
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            item = get_object_or_404(Item, item_id=item_id)

            return JsonResponse({
                "status": "success",
                "data": {
                    "item": item.name,
                    "te_price": item.TE_value,
                    "torn_price": item.market_value
                }
            })
        except Exception as E:
            return JsonResponse({
                "status": "error",
                "message": "Invalid request parameters", 
                "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})

@ce
def fetch_prices(request):
    """
    Example URL usage: /api/get_prices?item_id=<ITEM_ID>&sort_by=<SORT_BY>&order=<ORDER>&page=1
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            sort_by = request.GET.get('sort_by', 'price')  # Default sort by price
            order = request.GET.get('order', 'asc')  # Default order ascending
            page = request.GET.get('page', '1')

            item = get_object_or_404(Item, item_id=item_id)
            listings = Listing.objects.filter(item=item)

            if order == 'desc':
                sort_by = f'-{sort_by}'
            listings = listings.order_by(sort_by)

            paginator = Paginator(listings, 10)  # Show 10 per page

            try:
                page = int(page)
                paged_listings = paginator.page(page)
            except PageNotAnInteger:
                paged_listings = paginator.page(1)
            except EmptyPage:
                paged_listings = paginator.page(paginator.num_pages)

            return JsonResponse({
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
            })
        except Exception as E:
            return JsonResponse({
                "status": "error",
                "message": "Invalid request parameters", 
                "error": str(E),
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})
    
@ce
def fetch_best_price(request):
    """
    Example URL usage: /api/fetch_best_price?item_id=<ITEM_ID>
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            item = get_object_or_404(Item, item_id=item_id)

            listing = Listing.objects.filter(item=item).order_by('price').first()

            if listing:
                return JsonResponse({
                    "status": "success",
                    "data": {
                        "item": item.name,
                        "trader": listing.owner.name,
                        "price": listing.effective_price,
                    }
                })
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "No listings found for the specified item"
                })
            
        except Exception as E:
            return JsonResponse({
                "status": "error",
                "message": "Invalid request parameters", 
                "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})