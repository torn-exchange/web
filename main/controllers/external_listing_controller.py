import os
from django.db.models import Prefetch
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import Http404
from django.http import HttpResponse
from django.template.loader import render_to_string

from main.models import ExternalListing, ItemVariation, ExternalListingItem
from users.models import Profile

from html2image import Html2Image

class ExternalListingController:

    @method_decorator(login_required)
    def index(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

        queryset = ExternalListing.objects.filter(owner=profile)
        listings = list(queryset) if queryset.exists() else []

        return render(request, 'main/user/selling/external_listing/index.html', {
            'listings': listings
        })

    @method_decorator(login_required)
    def show(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

    @method_decorator(login_required)
    def destroy(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

    @method_decorator(login_required)
    def create(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

        queryset = ItemVariation.objects.filter(owner=profile)
        items = list(queryset) if queryset.exists() else []

        return render(request, 'main/user/selling/external_listing/create.html', {
            'items': items
        })

    @method_decorator(login_required)
    def store(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

    @method_decorator(login_required)
    def edit(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

    @method_decorator(login_required)
    def update(self, request):
        if not request.user.is_authenticated:
            messages.error(request, 'You first need to log in to view manage your external listings')
            return redirect('login')

        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            messages.error(request, 'Your profile is not set up. Please set up your profile first.')
            return redirect('login')

    def read_generate(self, request, uuid: str):
        listing = ExternalListing.objects.filter(uuid=uuid).first()
        if not listing:
            raise Http404()

        view_type = listing.view_type

        if view_type == 'image':
            image_url = request.build_absolute_uri(reverse('external_listings_read', args=[uuid]))

            output_dir = os.path.join(settings.BASE_DIR, 'static', 'main', 'images', 'external_listings')

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            hti = Html2Image(output_path=output_dir)
            hti.use_new_headless = True
            hti.browser.print_command = True

            output_filename = f"{uuid}.png"

            hti.screenshot_url(url=image_url, output_file=output_filename, size=(500, 200))

            # hti.screenshot(url=image_url, save_as=output_filename, size=(500, 200))

            output_path = os.path.join(output_dir, output_filename)

            # Open the image file and return it in the HTTP response
            with open(output_path, 'r') as image_file:
                response = HttpResponse(image_file.read(), content_type="image/png")
                return response

    def read(self, request, uuid: str):
        listing = ExternalListing.objects.filter(uuid=uuid).first()
        # if not listing:
        #     raise Http404()

        external_listings = ExternalListing.objects.prefetch_related(
            Prefetch('externallistingitem_set', queryset=ExternalListingItem.objects.all(), to_attr='items')
        )

        listings = []
        for ext_listing in external_listings:
            for ext_item in ext_listing.items:
                item_data = {
                    'item': ext_item.listing,  # This resolves to either Listing or ItemVariation
                    'rarity': getattr(ext_item.listing, 'rarity', 'common'),  # Ensure a default rarity
                    'price': getattr(ext_item.listing, 'price', 0),  # Default to 0 if price is missing
                }
                listings.append(item_data)

        return render(request, 'main/user/selling/external_listing/components/external_image_stub.html', {
            "STATIC_URL": request.build_absolute_uri(settings.STATIC_URL),
            'listings': listings
        })

        view_type = listing.view_type
        if view_type == 'image':
            html_content = render_to_string('main/user/selling/external_listing/components/external_image_stub.html', {
                'listings': listings,
                "STATIC_URL": request.build_absolute_uri(settings.STATIC_URL),
            })

            options = {
                "format": "png",
                "quality": 100,
                "enable-local-file-access": ""
            }
            image = imgkit.from_string(html_content, False, options=options)

            response = HttpResponse(image, content_type="image/png")
            return response


