import json
from unittest import mock

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import JoinCode, Membership, Notification, Term
from apps.shared.testing import add_seat, make_code, make_committee, make_org, make_user


class RedeemTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.joiner = make_user("joiner")
        self.client.force_login(self.joiner)

    def call(self, name, code="ABCD2345"):
        return self.client.post(reverse(name), json.dumps({"code": code}), content_type="application/json",
                                headers={"Accept": "application/json"})

    def test_preview_describes_the_seat_and_changes_nothing(self):
        c = make_committee(self.org)
        make_code(self.org, self.owner, role="COMMITTEE_HEAD", committee=c)
        r = self.call("join_preview", "abcd-2345")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["summary"], "You are about to join Test Society as Committee Head in Logistics, A.Y. 2026-2027. Confirm?")
        self.assertEqual(JoinCode.objects.get().uses_count, 0)
        self.assertFalse(Membership.objects.filter(user=self.joiner).exists())

    def test_redeem_creates_seat_on_active_term_and_counts_use(self):
        c = make_committee(self.org)
        code = make_code(self.org, self.owner, max_uses=2, committee=c)
        r = self.call("join_redeem")
        self.assertEqual(r.status_code, 201)
        seat = Membership.objects.get(user=self.joiner)
        self.assertEqual((seat.term, seat.role, seat.committee, str(seat.valid_until)), (self.term, "MEMBER", c, "2027-05-31"))
        code.refresh_from_db()
        self.assertEqual(code.uses_count, 1)
        self.assertEqual(Notification.objects.get().recipient, self.owner)

    def test_last_use_goes_to_the_first_person_only(self):
        make_code(self.org, self.owner, max_uses=1)
        self.assertEqual(self.call("join_redeem").status_code, 201)
        second = make_user("late")
        self.client.force_login(second)
        r = self.call("join_redeem")
        self.assertEqual(r.status_code, 409)
        self.assertIn("used up", r.json()["error"])
        self.assertFalse(Membership.objects.filter(user=second).exists())

    def test_unusable_codes_are_refused_with_a_reason(self):
        for kind, kw, word in [("revoked", {"revoked_at": timezone.now()}, "cancelled"), ("expired", {"hours": -1}, "expired")]:
            JoinCode.objects.all().delete()
            make_code(self.org, self.owner, **kw)
            r = self.call("join_redeem")
            self.assertEqual(r.status_code, 409, kind)
            self.assertIn(word, r.json()["error"])
        self.assertFalse(Membership.objects.filter(user=self.joiner).exists())

    def test_unknown_code_and_short_code(self):
        self.assertEqual(self.call("join_redeem", "ZZZZ9999").status_code, 404)
        self.assertEqual(self.call("join_redeem", "ZZ").status_code, 400)

    def test_no_redemption_unless_the_year_is_active(self):
        make_code(self.org, self.owner)
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()
        self.assertEqual(self.call("join_redeem").status_code, 409)

    def test_inactive_committee_blocks_its_code(self):
        make_code(self.org, self.owner, committee=make_committee(self.org, active=False))
        self.assertEqual(self.call("join_redeem").status_code, 409)

    def test_cannot_take_the_same_seat_twice_or_a_member_seat_as_a_leader(self):
        make_code(self.org, self.owner, max_uses=5)
        self.assertEqual(self.call("join_redeem").status_code, 201)
        self.assertEqual(self.call("join_redeem").status_code, 409)
        self.client.force_login(self.owner)
        self.assertEqual(self.call("join_redeem").status_code, 409)
        self.assertEqual(JoinCode.objects.get().uses_count, 1)

    def test_head_seat_already_taken(self):
        c = make_committee(self.org)
        add_seat(make_user(), self.org, self.term, Membership.Role.COMMITTEE_HEAD, c)
        make_code(self.org, self.owner, role="COMMITTEE_HEAD", committee=c)
        r = self.call("join_redeem")
        self.assertEqual(r.status_code, 409)
        self.assertIn("already has a Committee Head", r.json()["error"])

    def test_member_can_be_promoted_by_a_head_code(self):
        c = make_committee(self.org)
        add_seat(self.joiner, self.org, self.term, committee=c)
        make_code(self.org, self.owner, role="COMMITTEE_HEAD", committee=c)
        self.assertEqual(self.call("join_redeem").status_code, 201)
        self.assertEqual(Membership.objects.filter(user=self.joiner).count(), 2)

    def test_database_conflict_is_answered_and_rolled_back(self):
        code = make_code(self.org, self.owner)
        with mock.patch.object(Membership.objects, "create", side_effect=IntegrityError):
            r = self.call("join_redeem")
        self.assertEqual(r.status_code, 409)
        code.refresh_from_db()
        self.assertEqual(code.uses_count, 0)

    def test_too_many_wrong_codes_are_throttled(self):
        from django.core.cache import cache
        cache.clear()
        for _ in range(10):
            self.call("join_redeem", "ZZZZ9999")
        self.assertEqual(self.call("join_redeem", "ZZZZ9999").status_code, 429)
        cache.clear()

    def test_anonymous_gets_401_json(self):
        self.client.logout()
        self.assertEqual(self.call("join_redeem").status_code, 401)
