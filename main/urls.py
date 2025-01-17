"""fundbros URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.conf import settings
from django.views.generic import TemplateView

from . import views
from . import api

urlpatterns = [
    # REGULAR SITE
    path('', views.homepage, name='home'),
    path('edit_price_list', views.edit_price_list, name='edit_price_list'),
    path('prices/<str:identifier>/', views.price_list, name='price_list'),
    path('prices/', views.price_list, name='price_list'),
    path('calculator', views.calculator, name='calculator'),
    path('paste_parse', views.parse_trade_paste, name='trade_paste'),
    path('vote_view', views.vote_view, name='vote_view'),
    path('listings', views.listings, name='listings'),
    path('services/<str:identifier>/', views.services_list, name='services_list'),
    path('services/', views.services_list, name='services_list'),
    path('search_services/', views.search_services, name='search_services'),
    path('edit_services/', views.edit_services, name='edit_services'),
    path('create_receipt', views.create_receipt, name='create_receipt'),
    path('new_create_receipt', views.new_create_receipt, name='new_create_receipt'),
    path('receipt/<str:receipt_id>/', views.receipt_view, name='receipt_view'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/all_sellers/', views.all_sellers, name='all_sellers'),
    path('analytics/all_trades/', views.all_trades, name='all_trades'),
    path('delete_receipt/<str:receipt_id>/',
         views.delete_receipt_from_profile, name='delete_receipt'),
    path('about/', views.about, name='about'),
    path('settings/', views.settings, name='settings'),
    path('settings/<str:option>', views.settings, name='settings'),
    path('revives_listings', views.revives_listings, name='revives_listings'),
    path('losses_listings', views.losses_listings, name='losses_listings'),
    path('employee_listings', views.employee_listings, name='employee_listings'),
    path('extension_get_prices', views.extension_get_prices,
         name='extension_get_prices'),
    path('new_extension_get_prices', views.new_extension_get_prices,
         name='new_extension_get_prices'),
    path('company_listings', views.company_listings, name='company_listings'),
    path('companies_hiring', views.company_hiring_listings, name='companies_hiring'),
    path('museum_helper', views.museum_helper, name='museum_helper'),
    path('ads.txt', TemplateView.as_view(template_name='ads.txt')),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt')),
    
    # API
    path('api/', api.api_home, name='api_home'),
    path('api/test', api.test, name='test'),
    path('api/price', api.price, name='price'),
    path('api/get_profile_details', api.get_profile_details, name='get_profile_details'),
    path('api/te_price', api.TE_price, name='TE_price'),
    path('api/fetch_prices', api.fetch_prices, name='fetch_prices'),
    path('api/fetch_best_price', api.fetch_best_price, name='fetch_best_price'),

]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
        # other URLs
    ] + urlpatterns
