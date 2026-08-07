from datetime import timedelta

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

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
        six_months_ago = timezone.now() - timedelta(days=180)
        return (
            Profile.objects.filter(services__last_updated__gte=six_months_ago)
            .distinct()
            .order_by('id')
        )

    def location(self, profile):
        return reverse('services_list', args=[profile.name])


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # List of URL names from your navbar. Login-gated pages (edit_price_list,
        # manage_price_list, edit_services, calculator, analytics, settings) are
        # excluded, as are the bare 'price_list'/'services_list' routes (no
        # identifier), which redirect to login for anonymous visitors -- the
        # real per-trader pages are covered by TraderPriceListSitemap/
        # TraderServicesSitemap above.
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
            'api_home',
            'forum_tutorial',
            'about',
            'tos',
        ]

    def location(self, item):
        return reverse(item)
