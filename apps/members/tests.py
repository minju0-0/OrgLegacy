from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Membership, Term
from apps.shared.testing import add_seat, make_committee, make_org, make_user


class RosterTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.member = make_user("mem")
        self.seat = add_seat(self.member, self.org, self.term)
        self.list = reverse("member_list", args=[self.org.pk])

    def test_roster_lists_everyone_executives_first(self):
        self.client.force_login(self.member)
        r = self.client.get(self.list)
        seats = list(r.context["seats"])
        self.assertEqual([s.role for s in seats], ["EXECUTIVE", "MEMBER"])

    def test_only_executives_get_remove(self):
        self.client.force_login(self.member)
        self.assertNotContains(self.client.get(self.list), "member:remove")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.list), "member:remove")

    def test_executive_removes_a_member_who_is_told(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("member_remove", args=[self.org.pk, self.seat.pk]))
        self.assertFalse(Membership.objects.filter(pk=self.seat.pk).exists())
        self.assertEqual(self.member.notifications.count(), 1)

    def test_cannot_remove_self_executives_or_by_non_executive(self):
        own = Membership.objects.get(user=self.owner)
        self.client.force_login(self.owner)
        self.client.post(reverse("member_remove", args=[self.org.pk, own.pk]))
        self.assertTrue(Membership.objects.filter(pk=own.pk).exists())
        other_exec = add_seat(make_user(), self.org, self.term, Membership.Role.EXECUTIVE)
        self.client.post(reverse("member_remove", args=[self.org.pk, other_exec.pk]))
        self.assertTrue(Membership.objects.filter(pk=other_exec.pk).exists())
        self.client.force_login(self.member)
        r = self.client.post(reverse("member_remove", args=[self.org.pk, own.pk]))
        self.assertEqual(r.status_code, 403)


class LeaveTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.url = reverse("member_leave", args=[self.org.pk])

    def leave_json(self):
        return self.client.post(self.url, content_type="application/json", headers={"Accept": "application/json"})

    def test_member_leaves_and_org_disappears_from_home(self):
        m = make_user()
        add_seat(m, self.org, self.term)
        self.client.force_login(m)
        r = self.leave_json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["url"], reverse("home"))
        self.assertFalse(Membership.objects.filter(user=m).exists())
        self.assertEqual(self.client.get(reverse("home")).context["organizations"], [])

    def test_sole_executive_cannot_leave(self):
        self.client.force_login(self.owner)
        r = self.leave_json()
        self.assertEqual(r.status_code, 409)
        self.assertIn("only Executive", r.json()["error"])
        self.assertEqual(Membership.objects.count(), 1)

    def test_executive_can_leave_when_another_remains(self):
        add_seat(make_user(), self.org, self.term, Membership.Role.EXECUTIVE)
        self.client.force_login(self.owner)
        self.assertEqual(self.leave_json().status_code, 200)

    def test_leaving_keeps_closed_year_seats(self):
        m = make_user()
        old = Term.objects.create(organization=self.org, label="A.Y. 2025-2026", start_date="2025-06-01", end_date="2026-05-31", status=Term.Status.CLOSED)
        add_seat(m, self.org, old)
        add_seat(m, self.org, self.term)
        self.client.force_login(m)
        self.leave_json()
        self.assertEqual(list(Membership.objects.filter(user=m).values_list("term", flat=True)), [old.pk])

    def test_form_post_redirects_home_and_closed_only_seat_is_refused(self):
        m = make_user()
        add_seat(m, self.org, self.term)
        self.client.force_login(m)
        self.assertRedirects(self.client.post(self.url), reverse("home"))
        org2, term2, owner2 = make_org(name="Old", status=Term.Status.CLOSED)
        self.client.force_login(owner2)
        r = self.client.post(reverse("member_leave", args=[org2.pk]))
        self.assertRedirects(r, reverse("member_list", args=[org2.pk]))
        self.assertTrue(Membership.objects.filter(user=owner2).exists())


class LeavingEffectsTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.accounts.models import Event
        from apps.shared.testing import make_committee
        self.org, self.term, self.owner = make_org()
        self.logistics, self.creatives = make_committee(self.org, "Logistics"), make_committee(self.org, "Creatives")
        self.head_l, self.head_c = make_user("hl"), make_user("hc")
        add_seat(self.head_l, self.org, self.term, Membership.Role.COMMITTEE_HEAD, self.logistics)
        add_seat(self.head_c, self.org, self.term, Membership.Role.COMMITTEE_HEAD, self.creatives)
        self.member = make_user("leaver")
        add_seat(self.member, self.org, self.term, committee=self.logistics)
        today = timezone.localdate()
        self.upcoming = Event.objects.create(organization=self.org, term=self.term, title="Soon", date=today + timedelta(days=3), description="d", created_by=self.head_l)
        self.done = Event.objects.create(organization=self.org, term=self.term, title="Done", date=today - timedelta(days=3), description="d", created_by=self.owner)
        for e in (self.upcoming, self.done):
            e.volunteers.add(self.member)

    def leave(self):
        self.client.force_login(self.member)
        return self.client.post(reverse("member_leave", args=[self.org.pk]), content_type="application/json", headers={"Accept": "application/json"})

    def test_leaving_tells_executives_and_that_committees_head_only(self):
        self.assertEqual(self.leave().status_code, 200)
        note = "Leaver Test left Test Society."
        self.assertEqual(self.owner.notifications.filter(message=note).count(), 1)
        self.assertEqual(self.head_l.notifications.filter(message=note).count(), 1)
        self.assertEqual(self.head_c.notifications.filter(message=note).count(), 0)
        self.assertEqual(self.head_c.notifications.count(), 0)

    def test_leaving_drops_upcoming_volunteering_keeps_past_history_and_tells_the_planner(self):
        self.leave()
        self.assertFalse(self.upcoming.volunteers.filter(pk=self.member.pk).exists())
        self.assertTrue(self.done.volunteers.filter(pk=self.member.pk).exists())
        self.assertTrue(self.head_l.notifications.filter(message__contains="no longer a volunteer for Soon").exists())

    def test_being_removed_drops_upcoming_volunteering_too(self):
        seat = Membership.objects.get(user=self.member)
        self.client.force_login(self.owner)
        self.client.post(reverse("member_remove", args=[self.org.pk, seat.pk]))
        self.assertFalse(self.upcoming.volunteers.filter(pk=self.member.pk).exists())
        self.assertTrue(self.done.volunteers.filter(pk=self.member.pk).exists())

    def test_someone_with_a_second_seat_keeps_volunteering(self):
        add_seat(self.member, self.org, self.term, committee=self.creatives)
        seat = Membership.objects.get(user=self.member, committee=self.logistics)
        self.client.force_login(self.owner)
        self.client.post(reverse("member_remove", args=[self.org.pk, seat.pk]))
        self.assertTrue(self.upcoming.volunteers.filter(pk=self.member.pk).exists())
