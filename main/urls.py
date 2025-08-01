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
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from main.sitemap import StaticViewSitemap
from django.conf.urls.static import static

from . import views
from . import api

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # REGULAR SITE
    path('', views.homepage, name='home'),
    path('edit_price_list', views.edit_price_list, name='edit_price_list'),
    path('manage_price_list', views.manage_price_list, name='manage_price_list'),
    path('toggle_category_visibility', views.toggle_category_visibility, name='toggle_category_visibility'),
    path('save_category_order', views.save_category_order, name='save_category_order'),
    path('prices/<str:identifier>', views.price_list, name='price_list'),
    path('prices/<str:identifier>/', views.price_list, name='price_list'),
    path('prices/', views.price_list, name='price_list'),
    path('calculator', views.calculator, name='calculator'),
    path('paste_parse', views.parse_trade_paste, name='trade_paste'),
    path('vote_view', views.vote_view, name='vote_view'),
    path('listings', views.listings, name='listings'),
    path('rw_listings', views.rw_listings, name='rw_listings'),
    path('services/<str:identifier>', views.services_list, name='services_list'),
    path('services/<str:identifier>/', views.services_list, name='services_list'),
    path('services/', views.services_list, name='services_list'),
    path('search_services/', views.search_services, name='search_services'),
    path('edit_services/', views.edit_services, name='edit_services'),
    path('create_receipt', views.create_receipt, name='create_receipt'),
    path('new_create_receipt', views.new_create_receipt, name='new_create_receipt'),
    path('receipt/<str:receipt_id>', views.receipt_view, name='receipt_view'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/all_sellers/', views.all_sellers, name='all_sellers'),
    path('analytics/all_trades/', views.all_trades, name='all_trades'),
    path('analytics/mobile_all_trades/', views.mobile_all_trades, name='mobile_receipts'),
    path('delete_receipt/<str:receipt_id>/',
         views.delete_receipt_from_profile, name='delete_receipt'),
    path('about/', views.about, name='about'),
    path('settings/', views.settings, name='settings'),
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
    path("how-to-use-torn-exchange/", views.tutorial, name="forum_tutorial"),
    path('sitemap', views.sitemap, name='sitemap'),
    path('tos', views.tos, name='tos'),

    # STATIC FILES
    path('ads.txt', views.render_static, {'file': 'ads.txt'}, name='ads.txt'),
    path('robots.txt', views.render_static, {'file': 'robots.txt'}, name='robots.txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # API
    path('api/', api.api_home, name='api_home'),
    path('api/swagger.yaml', api.swag_yaml, name='Swagger'),
    path('api/status', api.test, name='api_status'),
    path('api/price', api.price, name='api_price'),
    path('api/profile', api.profile, name='api_profile'),
    path('api/te_price', api.TE_price, name='api_TE_price'),
    path('api/listings', api.listings, name='api_listings'),
    path('api/best_listing', api.best_listing, name='api_best_listing'),
    path('api/receipts', api.receipts, name='api_receipts'),
    path('api/sellers', api.sellers, name='api_sellers'),
    path('api/modify_listing', api.modify_listing, name='modify_listing'),
    path('api/active_traders', api.active_traders, name='active_traders'),
    
    # handle api/ paths that doesn't exist
    path('api/<str:invalid_path>', api.api_404, name='api_404'),
    
    # handle paths that don't exist
    re_path(r'^(?P<invalid_path>.+)/?$', views.custom_404, name='custom_404'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
        # other URLs
    ] + urlpatterns
