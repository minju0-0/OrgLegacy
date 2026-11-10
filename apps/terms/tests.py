from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Membership, Term, TermPlan
from apps.shared.testing import add_seat, make_org, make_user


def body(**kw):
    data = {"academic_year": "2027-2028", "start_date": "2027-06-01", "end_date": "2028-05-31"}
    data.update(kw)
    return data


class PlanTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.second = make_user("second")
        add_seat(self.second, self.org, self.term, Membership.Role.EXECUTIVE)
        self.member = make_user("mem")
        add_seat(self.member, self.org, self.term)
        self.page = reverse("term_plan", args=[self.org.pk])
        self.save = reverse("term_plan_save", args=[self.org.pk])

    def test_only_executives_reach_the_page_and_the_nav_item(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.page).status_code, 403)
        self.assertEqual(self.client.post(self.save, body()).status_code, 403)
        self.assertNotContains(self.client.get(reverse("organization_detail", args=[self.org.pk])), self.page)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("organization_detail", args=[self.org.pk])), self.page)

    def test_page_suggests_the_following_year(self):
        self.client.force_login(self.owner)
        r = self.client.get(self.page)
        self.assertContains(r, 'value="2027-2028"')
        self.assertContains(r, 'value="2027-06-01"')
        self.assertContains(r, 'value="2028-05-31"')

    def test_executive_sets_up_the_next_year_and_the_others_are_told(self):
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(self.save, body()), self.page)
        plan = TermPlan.objects.get()
        self.assertEqual((plan.term, plan.label, plan.start_date, plan.created_by), (self.term, "A.Y. 2027-2028", date(2027, 6, 1), self.owner))
        self.assertEqual(self.second.notifications.count(), 1)
        self.assertEqual(self.owner.notifications.count(), 0)
        self.assertEqual(Term.objects.count(), 1)           # a plan is not a Term, so the one-live-term rule is untouched

    def test_saving_again_changes_the_one_plan(self):
        self.client.force_login(self.owner)
        self.client.post(self.save, body())
        self.client.post(self.save, body(academic_year="2027–2028", end_date="2028-06-15"))
        self.assertEqual(TermPlan.objects.count(), 1)
        self.assertEqual(TermPlan.objects.get().end_date, date(2028, 6, 15))

    def test_validation_keeps_the_input_and_names_the_problem(self):
        self.client.force_login(self.owner)
        cases = [({"academic_year": "2027-2029"}, "two years in a row"),
                 ({"academic_year": "2026-2027"}, "already exists"),
                 ({"start_date": "2027-05-31"}, "must start after the current A.Y. ends"),
                 ({"end_date": "2027-06-01"}, "must end after it starts"),
                 ({"end_date": "2029-12-31"}, "18 months"),
                 ({"start_date": ""}, "Enter the day it starts")]
        for change, text in cases:
            r = self.client.post(self.save, body(**change))
            self.assertContains(r, text, status_code=400)
        self.assertFalse(TermPlan.objects.exists())

    def test_clear_removes_only_the_plan(self):
        self.client.force_login(self.owner)
        self.client.post(self.save, body())
        self.assertRedirects(self.client.post(reverse("term_plan_clear", args=[self.org.pk])), self.page)
        self.assertFalse(TermPlan.objects.exists())
        self.assertEqual(Term.objects.get().status, Term.Status.ACTIVE)

    def test_locked_once_awaiting_approval(self):
        self.client.force_login(self.owner)
        self.client.post(self.save, body())
        self.term.status = Term.Status.PENDING_SIGNOFF
        self.term.save()
        r = self.client.get(self.page)
        self.assertContains(r, "plan is locked")
        self.assertNotContains(r, "Clear plan</button>")
        self.assertRedirects(self.client.post(self.save, body(academic_year="2028-2029", start_date="2028-06-01", end_date="2029-05-31")),
                             reverse("organization_detail", args=[self.org.pk]))
        self.assertEqual(TermPlan.objects.get().label, "A.Y. 2027-2028")

    def test_overview_shows_the_plan_to_every_member_and_draws_it_on_the_shelf(self):
        self.client.force_login(self.owner)
        self.client.post(self.save, body())
        self.client.force_login(self.member)
        r = self.client.get(reverse("organization_detail", args=[self.org.pk]))
        self.assertContains(r, "A.Y. 2027-2028")
        self.assertContains(r, "spine--planned")
        self.assertEqual(r.context["next_plan"].label, "A.Y. 2027-2028")

    def test_overview_says_not_set_up_and_hides_plan_for_closed_years(self):
        self.client.force_login(self.member)
        self.assertContains(self.client.get(reverse("organization_detail", args=[self.org.pk])), "Not set up")
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.assertNotContains(self.client.get(reverse("organization_detail", args=[self.org.pk])), "Not set up")
