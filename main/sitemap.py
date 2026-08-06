from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from users.models import Profile


class TraderPriceListSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.6

    def items(self):
        return Profile.objects.filter(on_vacation=False, listing__hidden=False).distinct().order_by('id')

    def location(self, profile):
        return reverse('price_list', args=[profile.name])


class TraderServicesSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.5

    def items(self):
        return Profile.objects.filter(services__isnull=False).distinct().order_by('id')

    def location(self, profile):
        return reverse('services_list', args=[profile.name])


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # List of URL names from your navbar
        return [
            'home',
            'listings',
            'search_services',
            'employee_listings',
            'revives_listings',
            'losses_listings',
            'company_listings',
            'companies_hiring',
            'museum_helper',
            'price_list',
            'edit_price_list',
            'manage_price_list',
            'services_list',
            'edit_services',
            'calculator',
            'analytics',
            'settings',
            'api_home',
            'forum_tutorial',
            'about',
            'tos',
        ]

    def location(self, item):
        return reverse(item)
