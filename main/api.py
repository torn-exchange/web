import csv
import json
import os
from io import StringIO

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from main.filters import ListingFilter
from main.profile_stats import return_profile_stats
from .models import Item, Listing, Profile, TradeReceipt

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

@ce
def api_404(request, invalid_path=None):
    return JsonResponse({"status": "error", "message": "Endpoint not found"}, status=404)


def js(data, meta=None):
    if(meta):
        return JsonResponse({"status": "success", "meta": meta, "data": data})
    return JsonResponse({"status": "success", "data": data})


def je(message):
    return JsonResponse({"status": "error", "message": message})



### API functions ###

@ce
def swag_yaml(request):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'swagger.yaml')
    
    try:
        with open(file_path, 'r') as file:
            file_content = file.read()

        return HttpResponse(file_content, content_type='text/plain')
    
    except FileNotFoundError:
        return HttpResponse("File not found.", status=404)


def api_home(request):
    return render(request, 'swagger.html')


@ce
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
def price(request):
    # Example usage: /api/price?item_id=<ITEM_ID>?user_id=<USER_ID>
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
                return je("Listing not found")
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
def profile(request):
    """
    Example URL usage:
    /api/profile?user_id=<USER_ID>
    """
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            profile = Profile.objects.select_related('settings').filter(torn_id=user_id).get()

            return JsonResponse({
                "status": "success",
                "data": {
                    "name": profile.name,
                    "torn_id": profile.torn_id,
                    "activity_status": profile.activity_status,
                    "last_active": profile.last_active,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                    "votes": profile.vote_score,
                    "reviews": profile.settings.link_to_forum_post,
                }
            })
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
def TE_price(request):
    # Gets the TE MV from the database and compares it to torn MV
    # ExAmple URL usage: /api/TE_price?item_id=<ITEM_ID>
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            item = get_object_or_404(Item, item_id=item_id)
            
            data = {
                    "item": item.name,
                    "te_price": item.TE_value,
                    "torn_price": item.market_value
                }

            return js(data)
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
def listings(request):
    """
    Example URL usage: /api/get_prices?item_id=<ITEM_ID>&sort_by=<SORT_BY>&order=<ORDER>&page=1
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            page = request.GET.get('page', '1')

            item = get_object_or_404(Item, item_id=item_id)
            listings = Listing.objects.filter(item=item)
            
            # Apply ListingFilter
            filterset = ListingFilter(request.GET, queryset=listings)
            filtered_listings = filterset.qs
            
            # Handle pagination
            paginator = Paginator(filtered_listings, 20)
            try:
                paged_listings = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                paged_listings = paginator.page(1)

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
                            "price": listing.traders_price,
                            "item": listing.item.name
                        } for listing in paged_listings
                    ]
                }
            })
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
def best_listing(request):
    """
    Example URL usage: /api/best_listing?item_id=<ITEM_ID>
    """
    if request.method == 'GET':
        try:
            item_id = request.GET.get('item_id')
            item = get_object_or_404(Item, item_id=item_id)

            listing = Listing.objects.filter(item=item).order_by('price').first()

            if listing:
                return js({
                        "item": item.name,
                        "trader": listing.owner.name,
                        "price": listing.effective_price,
                    })
            else:
                return je("No listings found for the specified item")
            
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")


@ce
def receipts(request):
    """Get all receipts for a user

    Args:
        request (HttpRequest): HttpRequest object

    Returns:
        JSON: structured data of all receipts for a user
    """    
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
def sellers(request):
    """Get all sellers (customers) for a user

    Args:
        request (HTTPRequest): HTTPRequest object

    Returns:
        JSON: structured data of all sellers for a user
    """    
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
def modify_listing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            key = data.get('key')
            item_ids = data.get('item_ids', [])
            new_price = data.get('new_price')
            action = data.get('action')

            if not key or not item_ids or not action:
                return je("Missing required parameters")

            try:
                profile = Profile.objects.filter(api_key=key).get()
            except Profile.DoesNotExist:
                return je("Profile matching query does not exist")

            modified_listings = []
            for item_id in item_ids:
                item = get_object_or_404(Item, item_id=item_id)
                listing = Listing.objects.filter(owner=profile, item=item).first()

                if listing:
                    if action == 'update' and new_price:
                        try:
                            listing.price = int(new_price)
                            listing.save(update_fields=['price'])
                            modified_listings.append(item_id)
                        except Exception as e:
                            continue
                    elif action == 'delete':
                        listing.delete()
                        modified_listings.append(item_id)

            if modified_listings:
                return js(f"Listings modified successfully for items: {', '.join(modified_listings)}")
            else:
                return je("No listings were modified")
        except Exception as E:
            return je("Invalid request parameters")
    else:
        return je("Invalid HTTP method")