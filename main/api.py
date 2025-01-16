import csv
import json
from io import StringIO

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from main.profile_stats import return_profile_stats
from .models import Item, Listing, Profile, TradeReceipt

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

@csrf_exempt
def receipts(request):
    if request.method == 'GET':
        try:
            key = request.GET.get('key')
            output_format = request.GET.get('format')
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 100))
            
            profile = Profile.objects.filter(api_key=key).get()
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
                    "url": f'tornexchange.com/receipt/{receipt.receipt_url_string}',
                }
                for receipt in paged_receipts
            ]
            
            if output_format == "csv":
                return export_receipts_csv(data)
            
            return JsonResponse({
                    "status": "success",
                    "meta": {
                        "count": receipts.count(),
                        "page": page,
                        "per_page": per_page,
                        "total_pages": paginator.num_pages,
                    },
                    "data": data
                })
        except Exception as E:
            return JsonResponse({
                "status": "error", 
                "message": f"Invalid request parameters", "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})


@csrf_exempt
def sellers(request):
    if request.method == 'GET':
        try:
            key = request.GET.get('key')
            outputFormat = request.GET.get('format')
            
            profile = Profile.objects.filter(api_key=key).get()
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
                return export_sellers_csv(data)
            
            return JsonResponse({
                    "status": "success",
                    "meta": {
                        "count": len(sellers),
                    },
                    "data": data
                })
        except Exception as E:
            return JsonResponse({
                "status": "error", 
                "message": f"Invalid request parameters", "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})


def export_receipts_csv(data):
    # Create an in-memory file-like object
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["created_at", "seller", "url"])
    
    # Write the header
    writer.writeheader()

    # Write the data rows
    for row in data:
        writer.writerow(row)

    # Prepare the HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="receipts.csv"'

    # Write the CSV data to the response
    response.write(output.getvalue())
    return response


def export_sellers_csv(data):
    # Create an in-memory file-like object
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["name", "trades", "profit", "last_traded"])
    
    # Write the header
    writer.writeheader()

    # Write the data rows
    for row in data:
        writer.writerow(row)

    # Prepare the HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="receipts.csv"'

    # Write the CSV data to the response
    response.write(output.getvalue())
    return response
