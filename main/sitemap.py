from django.contrib.sitemaps import Sitemap
from django.urls import reverse

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
            'how-to-use-torn-exchange',
            'about',
            'tos',
        ]

    def location(self, item):
        return reverse(item)
