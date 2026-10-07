from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Event, Membership, Term
from apps.shared.testing import add_seat, make_committee, make_org, make_user


def body(**kw):
    data = {"title": "Orientation", "date": "2026-09-15", "description": "Welcomed freshmen.", "volunteers": "Ana", "challenges_lessons": "Start earlier.", "budget": "1500.50"}
    data.update(kw)
    return data


class EventTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.committee = make_committee(self.org)
        self.head, self.member = make_user("head"), make_user("mem")
        add_seat(self.head, self.org, self.term, Membership.Role.COMMITTEE_HEAD, self.committee)
        add_seat(self.member, self.org, self.term)
        self.list = reverse("event_list", args=[self.org.pk])
        self.new = reverse("event_create", args=[self.org.pk])

    def event(self, **kw):
        defaults = dict(organization=self.org, term=self.term, title="Fair", date=date(2026, 10, 1), description="d")
        defaults.update(kw)
        return Event.objects.create(**defaults)

    def test_non_member_gets_404(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(self.list).status_code, 404)

    def test_member_logs_an_event_but_cannot_set_the_budget(self):
        self.client.force_login(self.member)
        self.assertNotContains(self.client.get(self.new), 'name="budget"')
        r = self.client.post(self.new, body())
        e = Event.objects.get()
        self.assertRedirects(r, reverse("event_detail", args=[self.org.pk, e.pk]))
        self.assertEqual((e.term, e.organization, e.budget), (self.term, self.org, Decimal("0.00")))   # budget field was ignored

    def test_executive_sets_budget(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.new), 'name="budget"')
        self.client.post(self.new, body())
        self.assertEqual(Event.objects.get().budget, Decimal("1500.50"))

    def test_date_must_fall_inside_the_academic_year(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, body(date="2025-01-10"))
        self.assertContains(r, "Pick a date inside it", status_code=400)
        self.assertFalse(Event.objects.exists())

    def test_required_fields_and_negative_budget(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.new, body(title="  ", description=" ", budget="-5"))
        self.assertEqual(r.status_code, 400)
        for text in ("Give the event a name", "Say what the event was", "cannot be negative"):
            self.assertContains(r, text, status_code=400)

    def test_edit_is_for_heads_and_executives_not_members(self):
        e = self.event()
        url = reverse("event_edit", args=[self.org.pk, e.pk])
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.head)
        self.assertRedirects(self.client.post(url, body(title="Fair 2")), reverse("event_detail", args=[self.org.pk, e.pk]))
        e.refresh_from_db()
        self.assertEqual(e.title, "Fair 2")

    def test_head_edit_keeps_the_budget_an_executive_set(self):
        e = self.event(budget=Decimal("999.00"))
        self.client.force_login(self.head)
        self.client.post(reverse("event_edit", args=[self.org.pk, e.pk]), body(budget="1"))
        e.refresh_from_db()
        self.assertEqual(e.budget, Decimal("999.00"))

    def test_only_executives_delete(self):
        e = self.event()
        url = reverse("event_delete", args=[self.org.pk, e.pk])
        self.client.force_login(self.head)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Event.objects.exists())
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(url), self.list)
        self.assertFalse(Event.objects.exists())

    def test_detail_shows_controls_by_role(self):
        e = self.event()
        url = reverse("event_detail", args=[self.org.pk, e.pk])
        self.client.force_login(self.member)
        r = self.client.get(url)
        self.assertNotContains(r, "Delete event")
        self.assertNotContains(r, reverse("event_edit", args=[self.org.pk, e.pk]))
        self.client.force_login(self.owner)
        r = self.client.get(url)
        self.assertContains(r, "Delete event")
        self.assertContains(r, reverse("event_edit", args=[self.org.pk, e.pk]))

    def test_other_organizations_events_are_not_reachable(self):
        org2, term2, owner2 = make_org(name="Other")
        theirs = Event.objects.create(organization=org2, term=term2, title="Secret", date=date(2026, 10, 1), description="d")
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("event_detail", args=[self.org.pk, theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("event_delete", args=[self.org.pk, theirs.pk])).status_code, 404)
        self.assertTrue(Event.objects.filter(pk=theirs.pk).exists())

    def test_closed_year_is_read_only(self):
        e = self.event()
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.list), "read-only")
        self.assertNotContains(self.client.get(self.list), "Log an event")
        self.assertRedirects(self.client.post(self.new, body()), reverse("organization_detail", args=[self.org.pk]))
        self.client.post(reverse("event_delete", args=[self.org.pk, e.pk]))
        self.assertTrue(Event.objects.filter(pk=e.pk).exists())

    def test_alumnus_reads_only_the_year_they_served(self):
        org, closed, owner = make_org(name="Old", status=Term.Status.CLOSED)
        alum = make_user()
        add_seat(alum, org, closed)
        Event.objects.create(organization=org, term=closed, title="Then", date=date(2026, 10, 1), description="d")
        newer = Term.objects.create(organization=org, label="A.Y. 2027-2028", start_date=date(2027, 6, 1), end_date=date(2028, 5, 31), status=Term.Status.ACTIVE)
        Event.objects.create(organization=org, term=newer, title="Now", date=date(2027, 10, 1), description="d")
        self.client.force_login(alum)
        r = self.client.get(reverse("event_list", args=[org.pk]))
        self.assertContains(r, "Then")
        self.assertNotContains(r, "Now<")

    def test_list_puts_upcoming_first_then_past_latest_first(self):
        today = timezone.localdate()
        past_old = self.event(title="Old", date=today - timedelta(days=30))
        past_new = self.event(title="Recent", date=today - timedelta(days=2))
        later = self.event(title="Later", date=today + timedelta(days=20))
        soon = self.event(title="Soon", date=today + timedelta(days=3))
        self.client.force_login(self.member)
        rows = self.client.get(self.list).context["rows"]
        self.assertEqual([r["event"].title for r in rows], ["Soon", "Later", "Recent", "Old"])
        self.assertEqual([r["upcoming"] for r in rows], [True, True, False, False])


class EventSummaryTests(TestCase):
    def test_overview_glimpse_and_count_and_home_card_count(self):
        org, term, owner = make_org()
        today = timezone.localdate()
        for i, d in enumerate([today - timedelta(days=9), today - timedelta(days=5), today - timedelta(days=1), today + timedelta(days=4)]):
            Event.objects.create(organization=org, term=term, title=f"E{i}", date=d, description="d")
        self.client.force_login(owner)
        r = self.client.get(reverse("organization_detail", args=[org.pk]))
        self.assertEqual([e.title for e in r.context["recent_events"]], ["E3", "E2", "E1"])   # next one, then latest past
        self.assertEqual(r.context["counts"]["events"], 4)
        card = self.client.get(reverse("home")).context["organizations"][0]
        self.assertEqual(card["counts"], {"events": 4, "suppliers": 0, "notes": 0})

    def test_overview_without_events_has_no_events_section(self):
        org, term, owner = make_org()
        self.client.force_login(owner)
        self.assertNotContains(self.client.get(reverse("organization_detail", args=[org.pk])), "recent-title")
