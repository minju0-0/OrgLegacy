from django.test import TestCase
from django.urls import reverse

from apps.shared.testing import make_org


class SettingsTests(TestCase):
    def setUp(self):
        self.org, self.term, self.user = make_org()

    def test_save_notification_preferences_and_export_data(self):
        self.client.force_login(self.user)
        r1 = self.client.post(
            reverse("settings_save_notifications"),
            {"prefs": {"approval_requested": {"in_app": True, "email": False}}},
            content_type="application/json",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.post(
            reverse("settings_export"),
            {},
            content_type="application/json",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(r2.status_code, 200)
        dl_url = r2.json()["url"]

        r3 = self.client.get(dl_url)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3["Content-Type"], "application/json")
