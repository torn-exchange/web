from django.shortcuts import render, redirect
from .forms import UserRegisterForm
from django.contrib import messages
from django.contrib.auth import logout, login
from .models import Profile
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_protect
import requests
from django.utils.http import url_has_allowed_host_and_scheme

@csrf_protect
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.profile.torn_id = form.cleaned_data.get('torn_id')
            username = form.cleaned_data.get('username')
            user.save()
            messages.success(
                request, f'Your account has been created! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm
        
    context = {
        'page_title': 'Register - Torn Exchange',
        'form': form
    }
    return render(request, 'users/register.html', context)


@csrf_protect
def login_request(request):
    if request.method == 'POST':
        api_key = request.POST.get('apikey')
        req = requests.get(
            f'https://api.torn.com/user/?selections=basic&key={api_key}')
        data = json.loads(req.content)
        if data.get('error') is not None:
            messages.info(request, "Invalid API key.")
        else:
            player_name = data['name']
            player_id = str(data['player_id'])
            
            # login
            if player_id in [a['torn_id'] for a in Profile.objects.values('torn_id')]:
                profile = Profile.objects.filter(torn_id=player_id).first()

                if not profile.api_key:
                    messages.success(request, 'Your account has been created')
                else:
                    messages.success(request, f'Welcome back {player_name}!')

                profile.name = player_name
                profile.api_key = api_key
                profile.save()

                user = User.objects.filter(profile=profile).first()
                login(request, user)

                return redirect(request.GET.get('next') or 'home')
            else:  # register

                user = User.objects.create_user(player_id, 'johnpassword')
                user.save()
                user.refresh_from_db()
                user.profile.torn_id = player_id
                user.profile.api_key = api_key
                user.profile.name = player_name
                user.save()

                messages.success(request, 'Your account has been created')
                login(request, user)
                return redirect(request.GET.get('next') if url_has_allowed_host_and_scheme(request.GET.get('next'), allowed_hosts={request.get_host()}) else 'home')
    else:
        if request.user.is_authenticated:
            messages.error(request, 'You are already logged in!')
            return redirect("home")
        
    return render(request=request,
                  template_name="users/login.html",
                  context={})


def logout_request(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("home")
