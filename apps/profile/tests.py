from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import HandoverNote
from apps.shared.testing import make_org


class ProfileTests(TestCase):
    def setUp(self):
        self.org, self.term, self.user = make_org()
        HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Transition note.",
        )

    def test_profile_shows_real_stats(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)
        stats = {s["label"]: s["value"] for s in resp.context["profile_stats"]}
        self.assertEqual(stats["Handover notes"], 1)
