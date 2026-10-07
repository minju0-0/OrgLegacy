from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.shared.notify import notify
from apps.shared.testing import add_seat, make_code, make_org, make_user


class HomeDataTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.member = make_user()
        add_seat(self.member, self.org, self.term)

    def home(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("home"))

    def test_cards_link_to_the_organization_and_carry_its_id(self):
        card = self.home(self.owner).context["organizations"][0]
        self.assertEqual(card["id"], self.org.pk)
        self.assertEqual(card["url"], reverse("organization_detail", args=[self.org.pk]))

    def test_only_executives_get_the_share_code(self):
        code = make_code(self.org, self.owner, "SHAR3333", max_uses=25, hours=48)
        card = self.home(self.owner).context["organizations"][0]
        self.assertTrue(card["can_share_code"])
        self.assertEqual(card["join_code"], code.code)
        self.assertTrue(card["join_code_expires"].startswith("Expires"))
        self.assertFalse(self.home(self.member).context["organizations"][0].get("can_share_code"))

    def test_attention_lists_my_codes_that_expire_within_two_days(self):
        make_code(self.org, self.owner, "SOON2222", hours=20)
        make_code(self.org, self.owner, "LATER333", hours=200)
        items = self.home(self.owner).context["attention"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "invite")
        self.assertEqual(self.home(self.member).context["attention"], [])

    def test_activity_is_real_and_names_the_founder(self):
        feed = self.home(self.member).context["activity"]
        self.assertEqual({f["text"] for f in feed}, {"created the organization", "joined as Member"})

    def test_bell_shows_unread_and_marks_them_read(self):
        notify([self.member], "Hello there.", reverse("member_list", args=[self.org.pk]))
        r = self.home(self.member)
        self.assertEqual(r.context["notifications_unread"], 1)
        self.assertContains(r, "Hello there.")
        self.client.post(reverse("notifications_read_all"), content_type="application/json", headers={"Accept": "application/json"})
        self.assertEqual(self.home(self.member).context["notifications_unread"], 0)

    def test_notification_link_marks_read_and_never_leaves_the_site(self):
        notify([self.member], "Go", "https://evil.example/x")
        n = self.member.notifications.get()
        self.client.force_login(self.member)
        r = self.client.get(reverse("notifications_go", args=[n.pk]))
        self.assertRedirects(r, "/home/", fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.read)
        other = make_user()
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("notifications_go", args=[n.pk])).status_code, 404)
