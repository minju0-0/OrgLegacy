from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Event, EventLog, Membership, Term
from apps.shared.testing import add_seat, make_org, make_user


class LogTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.term.start_date = timezone.localdate() - timedelta(days=60)
        self.term.end_date = timezone.localdate() + timedelta(days=300)
        self.term.save()
        self.vol, self.vol2, self.plain = make_user("vol"), make_user("vol2"), make_user("plain")
        for u in (self.vol, self.vol2, self.plain):
            add_seat(u, self.org, self.term)
        today = timezone.localdate()
        self.past = Event.objects.create(organization=self.org, term=self.term, title="Done", date=today - timedelta(days=1), description="d", created_by=self.owner)
        self.today = Event.objects.create(organization=self.org, term=self.term, title="Today", date=today, description="d", created_by=self.owner)
        self.future = Event.objects.create(organization=self.org, term=self.term, title="Later", date=today + timedelta(days=4), description="d", created_by=self.owner)
        for e in (self.past, self.today, self.future):
            e.volunteers.add(self.vol, self.vol2)

    def add(self, event, **data):
        payload = {"what_happened": "We set up early.", "challenges_lessons": "Bring extension cords."}
        payload.update(data)
        return self.client.post(reverse("eventlog_add", args=[self.org.pk, event.pk]), payload)

    def page(self, event):
        return reverse("event_detail", args=[self.org.pk, event.pk])

    def test_volunteer_logs_on_a_past_event_and_everyone_sees_it_with_the_author(self):
        self.client.force_login(self.vol)
        self.assertRedirects(self.add(self.past), self.page(self.past))
        log = EventLog.objects.get()
        self.assertEqual((log.author, log.event, log.challenges_lessons), (self.vol, self.past, "Bring extension cords."))
        self.client.force_login(self.plain)
        r = self.client.get(self.page(self.past))
        self.assertContains(r, "We set up early.")
        self.assertContains(r, "Vol Test")
        self.assertNotContains(r, "Add your log")

    def test_event_day_opens_logging_but_a_later_day_does_not(self):
        self.client.force_login(self.vol)
        self.add(self.today)
        self.assertEqual(EventLog.objects.count(), 1)
        self.add(self.future)
        self.assertEqual(EventLog.objects.count(), 1)
        r = self.client.get(self.page(self.future))
        self.assertContains(r, "Logs open on")
        self.assertNotContains(r, "Add your log")

    def test_only_picked_volunteers_can_log_not_even_executives(self):
        for user in (self.plain, self.owner):
            self.client.force_login(user)
            self.add(self.past)
            self.assertNotContains(self.client.get(self.page(self.past)), "Add your log")
        self.assertFalse(EventLog.objects.exists())

    def test_a_volunteer_may_write_several_logs(self):
        self.client.force_login(self.vol)
        self.add(self.past)
        self.add(self.past, what_happened="Second thought.")
        self.assertEqual(EventLog.objects.filter(author=self.vol).count(), 2)

    def test_blank_or_oversized_logs_are_refused(self):
        self.client.force_login(self.vol)
        self.add(self.past, what_happened="   ")
        self.add(self.past, what_happened="a" * 5001)
        self.assertFalse(EventLog.objects.exists())

    def test_edit_is_the_authors_alone(self):
        log = EventLog.objects.create(event=self.past, author=self.vol, what_happened="mine")
        url = reverse("eventlog_edit", args=[self.org.pk, self.past.pk, log.pk])
        self.client.force_login(self.vol2)
        self.client.post(url, {"what_happened": "hijack"})
        self.client.force_login(self.owner)
        self.client.post(url, {"what_happened": "hijack"})
        log.refresh_from_db()
        self.assertEqual(log.what_happened, "mine")
        self.client.force_login(self.vol)
        self.client.post(url, {"what_happened": "better", "challenges_lessons": "l"})
        log.refresh_from_db()
        self.assertEqual((log.what_happened, log.challenges_lessons), ("better", "l"))

    def test_delete_by_author_or_executive_only(self):
        a = EventLog.objects.create(event=self.past, author=self.vol, what_happened="a")
        b = EventLog.objects.create(event=self.past, author=self.vol, what_happened="b")
        url = lambda log: reverse("eventlog_delete", args=[self.org.pk, self.past.pk, log.pk])
        self.client.force_login(self.vol2)
        self.client.post(url(a))
        self.assertEqual(EventLog.objects.count(), 2)
        self.client.force_login(self.vol)
        self.client.post(url(a))
        self.client.force_login(self.owner)
        self.client.post(url(b))
        self.assertFalse(EventLog.objects.exists())

    def test_a_log_cannot_be_reached_through_another_event(self):
        log = EventLog.objects.create(event=self.past, author=self.vol, what_happened="a")
        self.client.force_login(self.vol)
        r = self.client.post(reverse("eventlog_edit", args=[self.org.pk, self.today.pk, log.pk]), {"what_happened": "x"})
        self.assertEqual(r.status_code, 404)

    def test_closed_year_freezes_logs(self):
        log = EventLog.objects.create(event=self.past, author=self.vol, what_happened="keep")
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.vol)
        self.add(self.past)
        self.client.post(reverse("eventlog_delete", args=[self.org.pk, self.past.pk, log.pk]))
        self.assertEqual(list(EventLog.objects.values_list("what_happened", flat=True)), ["keep"])
        self.assertNotContains(self.client.get(self.page(self.past)), "Add your log")
