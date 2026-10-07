from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import JoinCode, Membership, Term
from apps.shared import codes
from apps.shared.testing import add_seat, make_code, make_committee, make_org, make_user


class IssueTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.logistics = make_committee(self.org, "Logistics")
        self.creatives = make_committee(self.org, "Creatives")
        self.head = make_user("head")
        add_seat(self.head, self.org, self.term, Membership.Role.COMMITTEE_HEAD, self.logistics)
        self.member = make_user("plain")
        add_seat(self.member, self.org, self.term)
        self.new = reverse("joincode_create", args=[self.org.pk])
        self.list = reverse("joincode_list", args=[self.org.pk])

    def test_plain_member_cannot_open_the_page_or_make_codes(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.list).status_code, 403)
        self.assertEqual(self.client.post(self.new, {"role": "MEMBER", "max_uses": 5, "hours": 24}).status_code, 403)

    def test_executive_makes_cross_committee_member_code(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, {"role": "MEMBER", "committee": "", "max_uses": 10, "hours": 168})
        self.assertRedirects(r, self.list)
        c = JoinCode.objects.get()
        self.assertEqual((c.role, c.committee, c.max_uses, c.created_by), ("MEMBER", None, 10, self.owner))
        self.assertEqual(len(c.code), 8)
        self.assertTrue(set(c.code) <= set(codes.ALPHABET))

    def test_executive_head_code_is_single_use_and_needs_a_committee(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, {"role": "COMMITTEE_HEAD", "committee": "", "max_uses": 50, "hours": 6})
        self.assertEqual(r.status_code, 400)
        r = self.client.post(self.new, {"role": "COMMITTEE_HEAD", "committee": self.creatives.pk, "max_uses": 50, "hours": 6})
        self.assertRedirects(r, self.list)
        c = JoinCode.objects.get()
        self.assertEqual((c.role, c.committee, c.max_uses), ("COMMITTEE_HEAD", self.creatives, 1))

    def test_head_code_cannot_last_days(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, {"role": "COMMITTEE_HEAD", "committee": self.creatives.pk, "max_uses": 1, "hours": 168})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(JoinCode.objects.exists())

    def test_no_head_code_for_a_committee_that_already_has_one(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, {"role": "COMMITTEE_HEAD", "committee": self.logistics.pk, "max_uses": 1, "hours": 6})
        self.assertContains(r, "already has a Committee Head", status_code=400)

    def test_committee_head_is_locked_to_own_committee_and_member_role(self):
        self.client.force_login(self.head)
        r = self.client.post(self.new, {"role": "COMMITTEE_HEAD", "max_uses": 1, "hours": 6})
        self.assertEqual(r.status_code, 400)
        r = self.client.post(self.new, {"role": "MEMBER", "committee": self.creatives.pk, "max_uses": 5, "hours": 24})
        self.assertEqual(r.status_code, 400)                                  # another committee is refused
        self.assertFalse(JoinCode.objects.exists())
        r = self.client.post(self.new, {"role": "MEMBER", "max_uses": 5, "hours": 24})
        self.assertRedirects(r, self.list)
        self.assertEqual(JoinCode.objects.get().committee, self.logistics)    # filled in from their own seat

    def test_head_only_sees_codes_for_their_committee(self):
        make_code(self.org, self.owner, "AAAA2222", committee=self.creatives)
        make_code(self.org, self.owner, "BBBB3333", committee=self.logistics)
        self.client.force_login(self.head)
        r = self.client.get(self.list)
        self.assertContains(r, "OL-BBBB-3333")
        self.assertNotContains(r, "OL-AAAA-2222")

    def test_revoke_by_issuer_or_executive_only(self):
        mine = make_code(self.org, self.head, "HEAD2222", committee=self.logistics)
        other = make_code(self.org, self.owner, "OWNR3333", committee=self.logistics)
        self.client.force_login(self.head)
        self.client.post(reverse("joincode_revoke", args=[self.org.pk, other.pk]))
        other.refresh_from_db()
        self.assertIsNone(other.revoked_at)
        self.client.post(reverse("joincode_revoke", args=[self.org.pk, mine.pk]))
        mine.refresh_from_db()
        self.assertIsNotNone(mine.revoked_at)
        self.client.force_login(self.owner)
        self.client.post(reverse("joincode_revoke", args=[self.org.pk, other.pk]))
        other.refresh_from_db()
        self.assertIsNotNone(other.revoked_at)

    def test_pending_year_cannot_issue(self):
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.new, {"role": "MEMBER", "max_uses": 5, "hours": 24}).status_code, 302)
        self.assertFalse(JoinCode.objects.exists())

    def test_quick_code_replaces_the_executives_previous_one(self):
        url = reverse("joincode_quick", args=[self.org.pk])
        self.client.force_login(self.owner)
        first = self.client.post(url, content_type="application/json", headers={"Accept": "application/json"}).json()
        second = self.client.post(url, content_type="application/json", headers={"Accept": "application/json"}).json()
        self.assertNotEqual(first["code"], second["code"])
        self.assertIsNotNone(JoinCode.objects.get(code=first["code"]).revoked_at)
        self.assertIsNone(JoinCode.objects.get(code=second["code"]).revoked_at)
        self.assertTrue(second["expires"].startswith("Expires"))

    def test_quick_code_is_executive_only_and_answers_json(self):
        url = reverse("joincode_quick", args=[self.org.pk])
        self.client.force_login(self.head)
        r = self.client.post(url, content_type="application/json", headers={"Accept": "application/json"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("error", r.json())


class CodeRulesTests(TestCase):
    def test_normalize_accepts_pasted_forms(self):
        self.assertEqual(codes.normalize("ol-4f7k-92qd"), "4F7K92QD")
        self.assertEqual(codes.normalize(" 4f7k 92qd "), "4F7K92QD")
        self.assertEqual(codes.normalize("4F7K"), "")

    def test_state_words(self):
        org, term, owner = make_org()
        c = make_code(org, owner, max_uses=1)
        self.assertEqual(codes.state(c), "active")
        c.uses_count = 1
        self.assertEqual(codes.state(c), "used")
        c.uses_count, c.revoked_at = 0, timezone.now()
        self.assertEqual(codes.state(c), "revoked")
        c.revoked_at, c.expires_at = None, timezone.now()
        self.assertEqual(codes.state(c), "expired")
