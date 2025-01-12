import json

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse


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
