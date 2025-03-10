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
    re_path(r'^edit_price_list/?$', views.edit_price_list, name='edit_price_list'),
    re_path(r'^manage_price_list/?$', views.manage_price_list, name='manage_price_list'),
    re_path(r'^toggle_category_visibility/?$', views.toggle_category_visibility, name='toggle_category_visibility'),
    re_path(r'^save_category_order/?$', views.save_category_order, name='save_category_order'),
    re_path(r'^prices/(?P<identifier>[\w-]+)/?$', views.price_list, name='price_list'),
    re_path(r'^prices/?$', views.price_list, name='price_list'),
    re_path(r'^calculator/?$', views.calculator, name='calculator'),
    re_path(r'^paste_parse/?$', views.parse_trade_paste, name='trade_paste'),
    re_path(r'^vote_view/?$', views.vote_view, name='vote_view'),
    re_path(r'^listings/?$', views.listings, name='listings'),
    re_path(r'^services/(?P<identifier>[\w-]+)/?$', views.services_list, name='services_list'),
    re_path(r'^services/?$', views.services_list, name='services_list'),
    re_path(r'^search_services/?$', views.search_services, name='search_services'),
    re_path(r'^edit_services/?$', views.edit_services, name='edit_services'),
    re_path(r'^create_receipt/?$', views.create_receipt, name='create_receipt'),
    re_path(r'^new_create_receipt/?$', views.new_create_receipt, name='new_create_receipt'),
    re_path(r'^receipt/(?P<receipt_id>[\w-]+)/?$', views.receipt_view, name='receipt_view'),
    re_path(r'^analytics/?$', views.analytics, name='analytics'),
    re_path(r'^analytics/all_sellers/?$', views.all_sellers, name='all_sellers'),
    re_path(r'^analytics/all_trades/?$', views.all_trades, name='all_trades'),
    re_path(r'^delete_receipt/(?P<receipt_id>[\w-]+)/?$', views.delete_receipt_from_profile, name='delete_receipt'),
    re_path(r'^about/?$', views.about, name='about'),
    re_path(r'^settings/(?P<option>[\w-]+)/?$', views.settings, name='settings'),
    re_path(r'^settings/?$', views.settings, name='settings'),
    re_path(r'^revives_listings/?$', views.revives_listings, name='revives_listings'),
    re_path(r'^losses_listings/?$', views.losses_listings, name='losses_listings'),
    re_path(r'^employee_listings/?$', views.employee_listings, name='employee_listings'),
    re_path(r'^extension_get_prices/?$', views.extension_get_prices, name='extension_get_prices'),
    re_path(r'^new_extension_get_prices/?$', views.new_extension_get_prices, name='new_extension_get_prices'),
    re_path(r'^company_listings/?$', views.company_listings, name='company_listings'),
    re_path(r'^companies_hiring/?$', views.company_hiring_listings, name='companies_hiring'),
    re_path(r'^museum_helper/?$', views.museum_helper, name='museum_helper'),
    re_path(r'^how-to-use-torn-exchange/?$', views.tutorial, name="forum_tutorial"),
    re_path(r'^sitemap/?$', views.sitemap, name='sitemap'),

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
