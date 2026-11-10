from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Event, EventLog, Membership, Term
from apps.shared.testing import add_seat, make_committee, make_org, make_user


def body(volunteers=(), **kw):
    data = {"title": "Orientation", "date": "2026-09-15", "description": "Welcome the freshmen.", "budget": "1500.50",
            "volunteers": [u.pk for u in volunteers]}
    data.update(kw)
    return data


class EventBase(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.logistics = make_committee(self.org, "Logistics")
        self.creatives = make_committee(self.org, "Creatives")
        self.head, self.member, self.other = make_user("head"), make_user("mem"), make_user("other")
        add_seat(self.head, self.org, self.term, Membership.Role.COMMITTEE_HEAD, self.logistics)
        add_seat(self.member, self.org, self.term)
        add_seat(self.other, self.org, self.term)
        self.list = reverse("event_list", args=[self.org.pk])
        self.new = reverse("event_create", args=[self.org.pk])

    def event(self, **kw):
        defaults = dict(organization=self.org, term=self.term, title="Fair", date=date(2026, 10, 1), description="d", created_by=self.owner)
        defaults.update(kw)
        return Event.objects.create(**defaults)


class PlanningTests(EventBase):
    def test_non_member_gets_404(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(self.list).status_code, 404)

    def test_members_read_but_cannot_plan(self):
        self.event()
        self.client.force_login(self.member)
        r = self.client.get(self.list)
        self.assertContains(r, "Fair")
        self.assertNotContains(r, "Add an event")
        self.assertEqual(self.client.post(self.new, body()).status_code, 403)
        self.assertEqual(Event.objects.count(), 1)

    def test_executive_plans_with_committee_budget_and_volunteers_and_future_date(self):
        future = (timezone.localdate() + timedelta(days=5)).isoformat()
        self.term.end_date = timezone.localdate() + timedelta(days=200)
        self.term.start_date = timezone.localdate() - timedelta(days=100)
        self.term.save()
        self.client.force_login(self.owner)
        r = self.client.post(self.new, body([self.member, self.other], date=future, committee=self.creatives.pk))
        e = Event.objects.get()
        self.assertRedirects(r, reverse("event_detail", args=[self.org.pk, e.pk]))
        self.assertEqual((e.created_by, e.committee, e.budget, e.term), (self.owner, self.creatives, Decimal("1500.50"), self.term))
        self.assertEqual(set(e.volunteers.all()), {self.member, self.other})
        self.assertEqual(self.member.notifications.count(), 1)           # told they were picked
        self.assertEqual(self.owner.notifications.count(), 0)

    def test_head_events_are_always_their_committees_and_carry_no_budget(self):
        self.client.force_login(self.head)
        r = self.client.get(self.list)
        self.assertNotContains(r, 'name="budget"')
        self.assertNotContains(r, 'name="committee"')
        self.client.post(self.new, body([self.member], committee=self.creatives.pk, budget="999"))
        e = Event.objects.get()
        self.assertEqual((e.committee, e.budget, e.created_by), (self.logistics, Decimal("0.00"), self.head))

    def test_volunteers_can_only_be_members_of_this_organization(self):
        outsider = make_user("outsider")
        self.client.force_login(self.owner)
        r = self.client.post(self.new, body([outsider]))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Event.objects.exists())

    def test_mistakes_reopen_the_dialog_and_keep_the_input(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, body(title="Kept", date="2020-01-01"))
        self.assertContains(r, "data-open-on-load", status_code=400)
        self.assertContains(r, "Kept", status_code=400)
        self.assertContains(r, "Pick a date inside it", status_code=400)
        r = self.client.post(self.new, body(title=" ", description=" ", budget="-5"))
        for text in ("Give the event a name", "Say what the event is for", "cannot be negative"):
            self.assertContains(r, text, status_code=400)

    def test_get_of_create_goes_back_to_the_list(self):
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(self.new), self.list)

    def test_list_order_and_counts(self):
        today = timezone.localdate()
        self.event(title="Old", date=today - timedelta(days=30))
        recent = self.event(title="Recent", date=today - timedelta(days=2))
        self.event(title="Later", date=today + timedelta(days=20))
        self.event(title="Soon", date=today + timedelta(days=3))
        recent.volunteers.add(self.member)
        EventLog.objects.create(event=recent, author=self.member, what_happened="x")
        self.client.force_login(self.member)
        rows = self.client.get(self.list).context["rows"]
        self.assertEqual([r["event"].title for r in rows], ["Soon", "Later", "Recent", "Old"])
        got = next(r["event"] for r in rows if r["event"].title == "Recent")
        self.assertEqual((got.volunteer_count, got.log_count), (1, 1))

    def test_closed_year_is_read_only(self):
        e = self.event()
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.list), "read-only")
        self.assertNotContains(self.client.get(self.list), "Add an event")
        self.assertRedirects(self.client.post(self.new, body()), reverse("organization_detail", args=[self.org.pk]))
        self.client.post(reverse("event_delete", args=[self.org.pk, e.pk]))
        self.assertTrue(Event.objects.filter(pk=e.pk).exists())

    def test_other_organizations_events_are_unreachable(self):
        org2, term2, _ = make_org(name="Other")
        theirs = Event.objects.create(organization=org2, term=term2, title="Secret", date=date(2026, 10, 1), description="d")
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("event_detail", args=[self.org.pk, theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("event_delete", args=[self.org.pk, theirs.pk])).status_code, 404)

    def test_alumnus_reads_only_the_year_they_served(self):
        org, closed, _ = make_org(name="Old", status=Term.Status.CLOSED)
        alum = make_user()
        add_seat(alum, org, closed)
        Event.objects.create(organization=org, term=closed, title="Then", date=date(2026, 10, 1), description="d")
        newer = Term.objects.create(organization=org, label="A.Y. 2027-2028", start_date=date(2027, 6, 1), end_date=date(2028, 5, 31), status=Term.Status.ACTIVE)
        Event.objects.create(organization=org, term=newer, title="Now", date=date(2027, 10, 1), description="d")
        self.client.force_login(alum)
        r = self.client.get(reverse("event_list", args=[org.pk]))
        self.assertContains(r, "Then")
        self.assertNotContains(r, "Now<")


class CorrectionTests(EventBase):
    def url(self, e, name="event_edit"):
        return reverse(name, args=[self.org.pk, e.pk])

    def test_members_cannot_edit(self):
        e = self.event()
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url(e)).status_code, 403)

    def test_head_edits_only_their_own_committees_events(self):
        mine = self.event(title="Mine", committee=self.logistics)
        theirs = self.event(title="Theirs", committee=self.creatives)
        whole = self.event(title="Whole")
        self.client.force_login(self.head)
        self.assertEqual(self.client.get(self.url(theirs)).status_code, 403)
        self.assertEqual(self.client.post(self.url(whole), body()).status_code, 403)
        self.assertRedirects(self.client.post(self.url(mine), body([self.member], title="Mine 2")), reverse("event_detail", args=[self.org.pk, mine.pk]))
        mine.refresh_from_db()
        self.assertEqual((mine.title, mine.committee), ("Mine 2", self.logistics))
        self.assertEqual(list(mine.volunteers.all()), [self.member])

    def test_head_edit_keeps_the_budget_an_executive_set(self):
        e = self.event(committee=self.logistics, budget=Decimal("999.00"))
        self.client.force_login(self.head)
        self.client.post(self.url(e), body(budget="1"))
        e.refresh_from_db()
        self.assertEqual(e.budget, Decimal("999.00"))

    def test_executive_edits_anything_and_new_volunteers_are_told_once(self):
        e = self.event()
        self.client.force_login(self.owner)
        self.client.post(self.url(e), body([self.member]))
        self.client.post(self.url(e), body([self.member, self.other]))
        self.assertEqual(self.member.notifications.count(), 1)
        self.assertEqual(self.other.notifications.count(), 1)

    def test_date_cannot_move_to_the_future_once_logs_exist(self):
        past = timezone.localdate() - timedelta(days=3)
        self.term.start_date = past - timedelta(days=10)
        self.term.end_date = past + timedelta(days=300)
        self.term.save()
        e = self.event(date=past)
        EventLog.objects.create(event=e, author=self.member, what_happened="x")
        self.client.force_login(self.owner)
        r = self.client.post(self.url(e), body(date=(timezone.localdate() + timedelta(days=2)).isoformat()))
        self.assertContains(r, "cannot move to a later date", status_code=400)

    def test_only_executives_delete_and_logs_go_with_the_event(self):
        e = self.event()
        EventLog.objects.create(event=e, author=self.member, what_happened="x")
        self.client.force_login(self.head)
        self.assertEqual(self.client.post(self.url(e, "event_delete")).status_code, 403)
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(self.url(e, "event_delete")), self.list)
        self.assertFalse(Event.objects.exists() or EventLog.objects.exists())

    def test_detail_controls_by_role(self):
        e = self.event(committee=self.logistics)
        for user, edit, delete in ((self.member, False, False), (self.head, True, False), (self.owner, True, True)):
            self.client.force_login(user)
            r = self.client.get(reverse("event_detail", args=[self.org.pk, e.pk]))
            self.assertEqual(self.url(e) in r.content.decode(), edit, user)
            self.assertEqual("Delete event" in r.content.decode(), delete, user)


class SummaryTests(EventBase):
    def test_overview_glimpse_count_and_home_count(self):
        today = timezone.localdate()
        for i, d in enumerate([today - timedelta(days=9), today - timedelta(days=5), today - timedelta(days=1), today + timedelta(days=4)]):
            self.event(title=f"E{i}", date=d)
        self.client.force_login(self.owner)
        r = self.client.get(reverse("organization_detail", args=[self.org.pk]))
        self.assertEqual([e.title for e in r.context["recent_events"]], ["E3", "E2", "E1"])
        self.assertEqual(r.context["counts"]["events"], 4)
        self.assertEqual(self.client.get(reverse("home")).context["organizations"][0]["counts"]["events"], 4)

    def test_overview_without_events_has_no_events_section(self):
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(reverse("organization_detail", args=[self.org.pk])), "recent-title")
