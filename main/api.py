import json

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

from .profile_stats import return_profile_stats

"""
The idea here is that /api will respond with a html page and then all the endpoints
will fall under /api/endpoint/

so I will start of with a /api/test endpoint that will respond with json output of the api status

"""

### API FUNCTIONS ###


### Actual API handling ###

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
    # Idea here is to take the userID of the trader and item ID as input via the request
    # I was thinking tornexchange.com/api/price?user_id=1&item_id=1

    if request.method == 'POST':
        try:
            # Get the user ID and item ID from the request
            user_id = request.POST.get('user_id')
            item_id = request.POST.get('item_id')

            # Need to double check some things on the db end before I can continue here

        except Exception as E:
            return JsonResponse({"status": "error", "message": f"Invalid request parameters", "error": str(E)})
