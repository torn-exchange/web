from django.shortcuts import render, redirect
from .forms import UserRegisterForm
from django.contrib import messages
from django.contrib.auth import logout, login
from .models import Profile
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_protect
import requests


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
    return render(request, 'users/register.html', {'form': form})


@csrf_protect
def login_request(request):
    if request.method == 'POST':
        api_key = request.POST.get('apikey')
        print(api_key)
        req = requests.get(
            f'https://api.torn.com/user/?selections=basic&key={api_key}')
        print(req)
        data = json.loads(req.content)
        print(data)
        if data.get('error') is not None:
            messages.info(request, "Invalid API key.")
        else:
            player_name = data['name']
            player_id = str(data['player_id'])
            (print(player_id in Profile.objects.all().values(
                'torn_id')), 'TEEEEEST \n \n \n \n \n')
            # login
            if player_id in [a['torn_id'] for a in Profile.objects.values('torn_id')]:
                print('logging IN ! \n \n \n')
                messages.success(request, f'Welcome back {player_name}!')
                profile = Profile.objects.filter(torn_id=player_id).get()
                profile.name = player_name
                profile.api_key = api_key
                profile.save()
                user = User.objects.filter(profile=profile).get()
                login(request, user)
                return redirect('/')
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
                return redirect('/')

        # if form.is_valid():
        #    username = form.cleaned_data.get('username')
        #    password = form.cleaned_data.get('password')
        #    user = authenticate(username=username, password=password)
        #    if user is not None:
        #        login(request, user)
        #        messages.info(request, f"You are now logged in as {username}")
        #        return redirect('/')
        #    else:

    else:
        pass
    return render(request=request,
                  template_name="users/login.html",
                  context={})


def logout_request(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("home")
