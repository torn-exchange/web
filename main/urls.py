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
from django.views.generic import TemplateView

from . import views
urlpatterns = [
    path('', views.homepage, name='home'),
    path('edit_price_list', views.edit_price_list, name='edit_price_list'),
    path('prices/<str:identifier>/', views.price_list, name='price_list'),
    path('prices', views.price_list, name='price_list'),
    path('calculator', views.calculator, name='calculator'),
    path('paste_parse', views.parse_trade_paste, name='trade_paste'),
    path('vote_view', views.vote_view, name='vote_view'),
    path('listings', views.listings, name='listings'),
    path('create_receipt', views.create_receipt, name='create_receipt'),
    path('new_create_receipt', views.new_create_receipt, name='new_create_receipt'),
    path('receipt/<str:receipt_id>/', views.receipt_view, name='receipt_view'),
    path('analytics/', views.analytics, name='analytics'),
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
    path('ads.txt', TemplateView.as_view(template_name='ads.txt')),
]
