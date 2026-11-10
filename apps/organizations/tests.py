from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Membership, Organization, Term
from apps.shared.testing import add_seat, make_org, make_user


class CharterTests(TestCase):
    def setUp(self):
        self.user = make_user("founder")
        self.client.force_login(self.user)
        self.url = reverse("organization_create")

    def post(self, **body):
        data = {"name": "Junior Computer Society", "acronym": "jcs", "academicYear": "2026-2027"}
        data.update(body)
        return self.client.post(self.url, data, content_type="application/json", headers={"Accept": "application/json"})

    def test_creates_organization_term_and_executive_together(self):
        r = self.post()
        self.assertEqual(r.status_code, 201)
        org = Organization.objects.get()
        term = Term.objects.get()
        seat = Membership.objects.get()
        self.assertEqual((org.acronym, term.label, term.status), ("JCS", "A.Y. 2026-2027", Term.Status.ACTIVE))
        self.assertEqual((seat.user, seat.role, seat.term), (self.user, Membership.Role.EXECUTIVE, term))
        self.assertEqual(str(term.start_date), "2026-06-01")
        self.assertEqual(str(term.end_date), "2027-05-31")
        self.assertEqual(r.json()["url"], reverse("organization_detail", args=[org.pk]))

    def test_rejects_bad_input_and_creates_nothing(self):
        for body, word in [({"name": "  "}, "name"), ({"academicYear": "2026-2028"}, "two years"),
                           ({"academicYear": "26-27"}, "two years"), ({"acronym": "A" * 13}, "acronym")]:
            r = self.post(**body)
            self.assertEqual(r.status_code, 400, body)
            self.assertIn(word, r.json()["error"])
        self.assertFalse(Organization.objects.exists())

    def test_en_dash_year_range_is_accepted(self):
        self.assertEqual(self.post(academicYear="2026\u20132027").status_code, 201)

    def test_double_submit_creates_one_organization(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(Organization.objects.count(), 1)

    def test_requires_login_and_post(self):
        self.client.logout()
        self.assertEqual(self.post().status_code, 401)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class OrganizationPageTests(TestCase):
    def test_non_member_gets_404_not_403(self):
        org, _, _ = make_org()
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("organization_detail", args=[org.pk])).status_code, 404)

    def test_page_describes_but_does_not_duplicate_the_sidebar_links(self):
        org, term, owner = make_org()
        member = make_user()
        add_seat(member, org, term)
        url = reverse("organization_detail", args=[org.pk])
        self.client.force_login(member)
        r = self.client.get(url)
        self.assertContains(r, "Test Society")
        self.assertNotContains(r, "Invite people")
        self.assertNotContains(r, "Inside")
        self.assertNotContains(r, reverse("joincode_list", args=[org.pk]))   # members never see the codes page
        self.client.force_login(owner)
        r = self.client.get(url)
        # The sidebar renders twice (desktop rail and mobile drawer); nothing in the page body links onward.
        self.assertContains(r, reverse("member_list", args=[org.pk]), count=2)
        self.assertContains(r, reverse("joincode_list", args=[org.pk]), count=2)

    def test_closed_year_is_read_only_and_says_so(self):
        org, term, owner = make_org(status=Term.Status.CLOSED)
        self.client.force_login(owner)
        r = self.client.get(reverse("organization_detail", args=[org.pk]))
        self.assertContains(r, "This A.Y. is closed")
        self.assertNotContains(r, "Invite people")

    def test_alumnus_sees_the_year_they_served(self):
        org, closed, owner = make_org(status=Term.Status.CLOSED)
        alum = make_user()
        add_seat(alum, org, closed)
        Term.objects.create(organization=org, label="A.Y. 2027-2028", start_date=closed.end_date, end_date=closed.end_date,
                            status=Term.Status.ACTIVE)
        self.client.force_login(alum)
        r = self.client.get(reverse("organization_detail", args=[org.pk]))
        self.assertEqual(r.context["term"], closed)
        self.assertEqual(len(r.context["years"]), 2)
