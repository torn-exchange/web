from django.contrib.auth.models import User
from django.test import TestCase

from main.models import ChangeLog


def make_user(username):
    user = User.objects.create(username=username)
    profile = user.profile
    profile.name = username
    profile.torn_id = username
    profile.save()
    return user, profile


class BazaarMvBannerTests(TestCase):

    def setUp(self):
        self.user, self.profile = make_user('bannertrader')
        self.client.force_login(self.user)

    def test_banner_shown_by_default(self):
        response = self.client.get('/edit_price_list')
        self.assertContains(response, 'bazaar-mv-banner')

    def test_banner_hidden_after_dismissal(self):
        self.client.post('/dismiss-bazaar-mv-banner')
        response = self.client.get('/edit_price_list')
        self.assertNotContains(response, 'bazaar-mv-banner')

    def test_dismiss_endpoint_requires_post(self):
        response = self.client.get('/dismiss-bazaar-mv-banner')
        self.assertEqual(response.status_code, 405)


class BazaarMvChangelogMigrationTests(TestCase):

    def test_changelog_entry_exists(self):
        self.assertTrue(
            ChangeLog.objects.filter(description__icontains='bazaar averages').exists()
        )
