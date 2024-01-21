from django.test import TestCase
from main.models import Item
from users.models import Profile, User

class AnimalTestCase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='user1')
        self.up1 = Profile.objects.create(user=self.u1,name='Hypochris', torn_id=12345, api_key='123456')

    def test_animals_can_speak(self):
        """Animals that can speak are correctly identified"""
        print('hey')

    def tearDown(self):
        self.up1.delete()
        self.u1.delete()