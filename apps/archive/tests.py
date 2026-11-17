from datetime import date
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Event, EventLog, HandoverNote, Supplier
from apps.shared.testing import make_org, make_user


class ArchiveTests(TestCase):
    def setUp(self):
        self.org, self.term, self.user = make_org()
        self.outsider = make_user("outsider")

        # Create sample event, log, supplier, and note
        self.event = Event.objects.create(
            organization=self.org,
            term=self.term,
            title="General Assembly 2026",
            date=date(2026, 7, 15),
            description="Welcome orientation for incoming freshmen.",
        )
        self.log = EventLog.objects.create(
            event=self.event,
            author=self.user,
            what_happened="Great turnout.",
            challenges_lessons="Sound system had microphone feedback.",
        )
        self.supplier = Supplier.objects.create(
            organization=self.org,
            name="Archival Printing Hub",
            contact_info="09171234567, printing@cebu.ph",
            cost_notes="Discounted 10% on bulk manuals.",
        )
        self.note = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Always book the auditorium at least one month ahead.",
        )

    def test_archive_search_overview(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("archive_search", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Institutional Memory Ledger")

    def test_search_finds_event_by_title_and_lesson(self):
        self.client.force_login(self.user)
        url = reverse("archive_search", args=[self.org.pk])
        resp = self.client.get(url, {"q": "Assembly"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "General Assembly 2026")

        resp2 = self.client.get(url, {"q": "feedback"})
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "General Assembly 2026")

    def test_search_finds_supplier_by_cost_notes(self):
        self.client.force_login(self.user)
        url = reverse("archive_search", args=[self.org.pk])
        resp = self.client.get(url, {"q": "manuals"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Archival Printing Hub")

    def test_search_finds_handover_note(self):
        self.client.force_login(self.user)
        url = reverse("archive_search", args=[self.org.pk])
        resp = self.client.get(url, {"q": "auditorium"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Always book the auditorium")

    def test_filter_by_kind(self):
        self.client.force_login(self.user)
        url = reverse("archive_search", args=[self.org.pk])
        # "Archival" is in supplier name and we search with kind=events
        resp = self.client.get(url, {"q": "Archival", "kind": "events"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Archival Printing Hub")

        # Now search with kind=suppliers
        resp2 = self.client.get(url, {"q": "Archival", "kind": "suppliers"})
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "Archival Printing Hub")

    def test_outsider_gets_404(self):
        self.client.force_login(self.outsider)
        resp = self.client.get(reverse("archive_search", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_global_search_json_and_cross_term_archive_links(self):
        # Close current term and open a new term; verify archived event & note details still open (200, not 404)
        self.term.status = "CLOSED"
        self.term.save()
        from apps.accounts.models import Membership, Term
        new_term = Term.objects.create(
            organization=self.org,
            label="A.Y. 2027-2028",
            start_date=date(2027, 6, 1),
            end_date=date(2028, 5, 31),
            status=Term.Status.ACTIVE,
        )
        Membership.objects.create(
            user=self.user,
            organization=self.org,
            term=new_term,
            role=Membership.Role.EXECUTIVE,
        )

        self.client.force_login(self.user)
        # Archived event and handover note from closed A.Y. 2026-2027 remain accessible as read-only
        ev_resp = self.client.get(reverse("event_detail", args=[self.org.pk, self.event.pk]))
        self.assertEqual(ev_resp.status_code, 200)
        self.assertContains(ev_resp, "This A.Y. is closed")

        note_resp = self.client.get(reverse("handover_detail", args=[self.org.pk, self.note.pk]))
        self.assertEqual(note_resp.status_code, 200)
        self.assertContains(note_resp, "This A.Y. is closed")

        # Global topbar search JSON endpoint
        srch = self.client.get(reverse("global_search"), {"q": "General Assembly"})
        self.assertEqual(srch.status_code, 200)
        groups = srch.json()
        self.assertTrue(any(g["label"] == "Events" for g in groups))
