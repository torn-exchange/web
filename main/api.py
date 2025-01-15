import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Listing, Profile, Item

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
            result = "API is working"
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
                "message": "Invalid request parameters", 
                "error": str(E)
            })
    else:
        return JsonResponse({"status": "error", "message": "Invalid HTTP method"})

@csrf_exempt
def get_profile_details(request):
    """
    Example URL usage:
    /api/get_profile_details?user_id=<USER_ID>&api_key=<API_KEY>
    """
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            api_key = request.GET.get('api_key')
            
            profile = get_object_or_404(Profile, torn_id=user_id)

            if profile.api_key != api_key:
                return JsonResponse({"status": "error", "message": "Authentication failed"})

            return JsonResponse({
                "status": "success",
                "data": {
                    "name": profile.name,
                    "torn_id": profile.torn_id,
                    "api_key": profile.api_key,
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
