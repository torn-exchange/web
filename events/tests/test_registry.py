from django.test import TestCase
from unittest.mock import patch

from events import registry


class RegistryTests(TestCase):
    def test_all_events_contains_elimination(self):
        keys = [e.key for e in registry.all_events()]
        self.assertIn("elimination", keys)

    def test_get_event(self):
        self.assertIsNotNone(registry.get_event("elimination"))
        self.assertIsNone(registry.get_event("nope"))

    def test_active_events_filters_by_is_active(self):
        with patch("events.config.ELIMINATION_ENABLED", False):
            self.assertEqual(registry.active_events(), [])
        with patch("events.config.ELIMINATION_ENABLED", True):
            self.assertEqual([e.key for e in registry.active_events()], ["elimination"])
