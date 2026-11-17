from datetime import date
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Membership, Term, TermPlan, TermSignOff
from apps.shared.testing import add_seat, make_org, make_user


class SignOffTests(TestCase):
    def setUp(self):
        self.org, self.term, self.exec1 = make_org()
        self.exec2 = make_user("exec2")
        add_seat(self.exec2, self.org, self.term, role=Membership.Role.EXECUTIVE)
        self.member = make_user("member1")
        add_seat(self.member, self.org, self.term, role=Membership.Role.MEMBER)

        # Create TermPlan for testing succession
        self.plan = TermPlan.objects.create(
            term=self.term,
            label="A.Y. 2027-2028",
            start_date=date(2027, 6, 1),
            end_date=date(2028, 5, 31),
            created_by=self.exec1,
        )

    def test_executive_and_members_page_access(self):
        self.client.force_login(self.exec1)
        resp = self.client.get(reverse("signoff_page", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 200)

        # Member can view read-only page
        self.client.force_login(self.member)
        resp2 = self.client.get(reverse("signoff_page", args=[self.org.pk]))
        self.assertEqual(resp2.status_code, 200)

    def test_cannot_initiate_without_next_plan(self):
        self.plan.delete()
        self.client.force_login(self.exec1)
        resp = self.client.post(reverse("signoff_initiate", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 302)
        self.term.refresh_from_db()
        self.assertEqual(self.term.status, Term.Status.ACTIVE)

    def test_initiate_sets_pending_signoff(self):
        self.client.force_login(self.exec1)
        resp = self.client.post(reverse("signoff_initiate", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 302)
        self.term.refresh_from_db()
        self.assertEqual(self.term.status, Term.Status.PENDING_SIGNOFF)

    def test_multi_executive_unanimous_signoff_rollover(self):
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()

        # Exec1 votes APPROVED
        self.client.force_login(self.exec1)
        resp1 = self.client.post(
            reverse("signoff_vote", args=[self.org.pk]),
            {"decision": TermSignOff.Decision.APPROVED},
        )
        self.assertEqual(resp1.status_code, 302)
        self.term.refresh_from_db()
        # Not yet finalized because exec2 hasn't voted
        self.assertEqual(self.term.status, Term.Status.PENDING_SIGNOFF)

        # Exec2 votes APPROVED -> UNANIMOUS!
        self.client.force_login(self.exec2)
        resp2 = self.client.post(
            reverse("signoff_vote", args=[self.org.pk]),
            {"decision": TermSignOff.Decision.APPROVED},
        )
        self.assertEqual(resp2.status_code, 302)

        # Old term is now CLOSED
        self.term.refresh_from_db()
        self.assertEqual(self.term.status, Term.Status.CLOSED)

        # New term was created from TermPlan and is now ACTIVE
        new_term = Term.objects.get(organization=self.org, status=Term.Status.ACTIVE)
        self.assertEqual(new_term.label, "A.Y. 2027-2028")

        # Executives rolled over to new term
        self.assertTrue(
            Membership.objects.filter(
                user=self.exec1, term=new_term, role=Membership.Role.EXECUTIVE
            ).exists()
        )
        self.assertTrue(
            Membership.objects.filter(
                user=self.exec2, term=new_term, role=Membership.Role.EXECUTIVE
            ).exists()
        )

        # Old TermPlan is cleared
        self.assertFalse(TermPlan.objects.filter(term=self.term).exists())

    def test_changes_requested_reverts_to_active(self):
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()

        self.client.force_login(self.exec1)
        resp = self.client.post(
            reverse("signoff_vote", args=[self.org.pk]),
            {
                "decision": TermSignOff.Decision.CHANGES_REQUESTED,
                "feedback": "Please add financial reconciliation notes.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.term.refresh_from_db()
        self.assertEqual(self.term.status, Term.Status.ACTIVE)

        # All signoffs are cleared for revisions
        self.assertEqual(TermSignOff.objects.filter(term=self.term).count(), 0)

    def test_cancel_signoff_reverts_to_active(self):
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()

        self.client.force_login(self.exec1)
        resp = self.client.post(reverse("signoff_cancel", args=[self.org.pk]))
        self.assertEqual(resp.status_code, 302)
        self.term.refresh_from_db()
        self.assertEqual(self.term.status, Term.Status.ACTIVE)
