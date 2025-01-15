import json

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Listing, Profile, Item

from .profile_stats import return_profile_stats

"""
The idea here is that /api will respond with a html page and then all the endpoints
will fall under /api/endpoint/

so I will start of with a /api/test endpoint that will respond with json output of the api status

"""

def api_home(request):
    return render(request, 'main/api_home.html')


@csrf_exempt
def test(request):
    if request.method == 'GET':
        try:
            result = f"API is working"

            return JsonResponse({"status": "success", "result": result})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"})
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})


@csrf_exempt
def get_item_price(request):
    
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
                "message": f"Invalid request parameters", "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})
