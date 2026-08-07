import json
import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from main.models import Item, Listing, Service, Services, ServiceCategories
from users.models import Profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username):
    user = User.objects.create(username=username)
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    profile.save()
    return profile


def make_item(name='Test Item', te_value=100_000, item_id=1):
    return Item.objects.create(
        name=name,
        description='',
        requirement='',
        item_type='Melee',
        weapon_type=None,
        buy_price=0,
        sell_price=0,
        market_value=te_value,
        circulation=10000,
        image_url='',
        TE_value=te_value,
        item_id=item_id,
    )


def make_listing(profile, item, price=100):
    return Listing.objects.create(owner=profile, item=item, price=price)


def make_service_offer(profile, name='Reviving', last_updated=None):
    service = Service.objects.create(name=name, description='', category=ServiceCategories.Other)
    offer = Services.objects.create(owner=profile, service=service, money_price=100, barter_price='', offer_description='')
    if last_updated is not None:
        Services.objects.filter(pk=offer.pk).update(last_updated=last_updated)
        offer.refresh_from_db()
    return offer


def extract_ld_json(html):
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Meta description / OG / Twitter tags
# ---------------------------------------------------------------------------

class MetaDescriptionTests(TestCase):

    def test_home_page_has_meta_description(self):
        response = self.client.get('/')
        html = response.content.decode()
        self.assertIn('<meta name="description" content=', html)

    def test_price_list_page_uses_per_trader_description(self):
        profile = make_user('descriptiontrader')
        profile.settings.trade_list_description = 'Buy my rare items cheap!'
        profile.settings.save()
        item = make_item(item_id=101)
        make_listing(profile, item)

        response = self.client.get(f'/prices/{profile.name}')
        html = response.content.decode()

        self.assertIn('Buy my rare items cheap!', html)
        self.assertNotIn(
            'Trade smarter with Torn Exchange - Your trusted marketplace for Torn City items',
            html,
        )
        # description must appear in the meta/OG/Twitter description tags (plus once
        # more in the page body, where the trader's description is shown to visitors)
        self.assertEqual(html.count('Buy my rare items cheap!'), 4)


# ---------------------------------------------------------------------------
# JSON-LD structured data
# ---------------------------------------------------------------------------

class StructuredDataTests(TestCase):

    def test_price_list_json_ld_is_valid_json(self):
        profile = make_user('jsonldtrader')
        item = make_item(name='Xanax', item_id=102)
        make_listing(profile, item)

        response = self.client.get(f'/prices/{profile.name}')
        html = response.content.decode()

        blob = extract_ld_json(html)
        self.assertIsNotNone(blob)
        data = json.loads(blob)
        self.assertEqual(data['@type'], 'ItemList')
        self.assertEqual(data['itemListElement'][0]['item']['name'], 'Xanax')

    def test_json_ld_escapes_special_characters(self):
        profile = make_user('xsstrader')
        item = make_item(name='Evil</script><script>alert(1)</script>Item', item_id=103)
        make_listing(profile, item)

        response = self.client.get(f'/prices/{profile.name}')
        html = response.content.decode()

        blob = extract_ld_json(html)
        self.assertNotIn('</script>', blob)

        data = json.loads(blob)
        self.assertEqual(
            data['itemListElement'][0]['item']['name'],
            'Evil</script><script>alert(1)</script>Item',
        )

    def test_home_page_has_organization_schema(self):
        response = self.client.get('/')
        html = response.content.decode()

        blob = extract_ld_json(html)
        self.assertIsNotNone(blob)
        data = json.loads(blob)
        self.assertEqual(data['@type'], 'Organization')


# ---------------------------------------------------------------------------
# robots.txt / llms.txt / sitemap
# ---------------------------------------------------------------------------

class CrawlerFilesTests(TestCase):

    def test_robots_txt_allows_ai_crawlers_and_lists_sitemap(self):
        response = self.client.get('/robots.txt')
        content = response.content.decode()
        self.assertIn('GPTBot', content)
        self.assertIn('Sitemap:', content)

    def test_llms_txt_served(self):
        response = self.client.get('/llms.txt')
        self.assertEqual(response.status_code, 200)

    def test_sitemap_includes_trader_price_list_url(self):
        profile = make_user('sitemaptrader')
        item = make_item(item_id=104)
        make_listing(profile, item)

        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        self.assertIn(f'/prices/{profile.name}', content)

    def test_sitemap_excludes_traders_with_no_visible_listings(self):
        make_user('notrader')

        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        self.assertNotIn('/prices/notrader', content)

    def test_sitemap_excludes_login_gated_pages(self):
        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        for path in ('/edit_price_list', '/manage_price_list', '/edit_services/',
                     '/calculator', '/analytics/', '/settings/'):
            self.assertNotIn(path, content)
        # the bare (no-identifier) routes redirect anonymous visitors to login
        self.assertNotIn('/prices/</loc>', content)
        self.assertNotIn('/services/</loc>', content)

    def test_sitemap_includes_recently_updated_service(self):
        profile = make_user('freshservicetrader')
        make_service_offer(profile, last_updated=timezone.now() - timedelta(days=30))

        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        self.assertIn(f'/services/{profile.name}', content)

    def test_sitemap_excludes_stale_service(self):
        profile = make_user('staleservicetrader')
        make_service_offer(profile, last_updated=timezone.now() - timedelta(days=200))

        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        self.assertNotIn(f'/services/{profile.name}', content)
