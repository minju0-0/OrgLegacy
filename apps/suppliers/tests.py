from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Membership, Supplier, SupplierRating, Term
from apps.shared.testing import add_seat, make_committee, make_org, make_user


def body(**kw):
    data = {"name": "Happy Prints", "contact_info": "0917 000 0000", "cost_notes": "PHP 12 per page"}
    data.update(kw)
    return data


class SupplierTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.head, self.member = make_user("head"), make_user("mem")
        add_seat(self.head, self.org, self.term, Membership.Role.COMMITTEE_HEAD, make_committee(self.org))
        add_seat(self.member, self.org, self.term)
        self.list = reverse("supplier_list", args=[self.org.pk])
        self.add = reverse("supplier_create", args=[self.org.pk])

    def supplier(self, **kw):
        defaults = dict(organization=self.org, name="Caterer", contact_info="x")
        defaults.update(kw)
        return Supplier.objects.create(**defaults)

    def test_non_member_gets_404(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(self.list).status_code, 404)

    def test_everyone_reads_but_only_executives_see_add(self):
        self.supplier()
        for user in (self.member, self.head):
            self.client.force_login(user)
            r = self.client.get(self.list)
            self.assertContains(r, "Caterer")
            self.assertNotContains(r, "Add a supplier")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.list), "Add a supplier")

    def test_executive_adds_and_lands_on_the_supplier(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.add, body(name="  Happy   Prints "))
        s = Supplier.objects.get()
        self.assertRedirects(r, reverse("supplier_detail", args=[self.org.pk, s.pk]))
        self.assertEqual((s.name, s.organization), ("Happy Prints", self.org))

    def test_members_and_heads_cannot_add_edit_or_delete(self):
        s = self.supplier()
        for user in (self.member, self.head):
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.add, body()).status_code, 403)
            self.assertEqual(self.client.post(reverse("supplier_edit", args=[self.org.pk, s.pk]), body(name="Hacked")).status_code, 403)
            self.assertEqual(self.client.post(reverse("supplier_delete", args=[self.org.pk, s.pk])).status_code, 403)
        s.refresh_from_db()
        self.assertEqual((s.name, Supplier.objects.count()), ("Caterer", 1))

    def test_validation_keeps_the_dialog_open_with_input_kept(self):
        self.supplier(name="Caterer")
        self.client.force_login(self.owner)
        r = self.client.post(self.add, body(name="caterer", contact_info="  "))
        self.assertContains(r, "already lists a supplier", status_code=400)
        self.assertContains(r, "Add at least one way to reach them", status_code=400)
        self.assertContains(r, "data-open-on-load", status_code=400)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_edit_allows_own_name_and_a_mistake_reopens_the_edit_dialog(self):
        a, b = self.supplier(name="A"), self.supplier(name="B")
        self.client.force_login(self.owner)
        url = reverse("supplier_edit", args=[self.org.pk, a.pk])
        r = self.client.post(url, body(name="B"))
        self.assertContains(r, "data-open-on-load", status_code=400)
        self.assertContains(r, "<h1 class=\"page-head__title\">A</h1>", status_code=400)   # still shows the saved name
        self.assertRedirects(self.client.post(url, body(name="a", cost_notes="new")), reverse("supplier_detail", args=[self.org.pk, a.pk]))
        a.refresh_from_db()
        self.assertEqual((a.name, a.cost_notes), ("a", "new"))

    def test_delete_takes_ratings_with_it(self):
        s = self.supplier()
        SupplierRating.objects.create(supplier=s, rated_by=self.member, score=4)
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(reverse("supplier_delete", args=[self.org.pk, s.pk])), self.list)
        self.assertFalse(Supplier.objects.exists() or SupplierRating.objects.exists())

    def test_other_organizations_suppliers_are_unreachable(self):
        org2, _, owner2 = make_org(name="Other")
        theirs = Supplier.objects.create(organization=org2, name="Theirs", contact_info="x")
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("supplier_detail", args=[self.org.pk, theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("supplier_delete", args=[self.org.pk, theirs.pk])).status_code, 404)
        self.assertTrue(Supplier.objects.filter(pk=theirs.pk).exists())

    def test_directory_shows_average_and_count_and_outlives_the_year(self):
        s = self.supplier()
        for user, score in ((self.member, 5), (self.head, 4)):
            SupplierRating.objects.create(supplier=s, rated_by=user, score=score)
        self.client.force_login(self.member)
        r = self.client.get(self.list)
        self.assertContains(r, "4.5")
        self.assertContains(r, "2 ratings")
        # the A.Y. closes: the directory is still readable, but nothing can be changed
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.owner)
        r = self.client.get(self.list)
        self.assertContains(r, "Caterer")
        self.assertNotContains(r, "Add a supplier")
        self.assertRedirects(self.client.post(self.add, body()), reverse("organization_detail", args=[self.org.pk]))

    def test_overview_counts_suppliers(self):
        self.supplier()
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("organization_detail", args=[self.org.pk])).context["counts"]["suppliers"], 1)


class RatingTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.member = make_user("mem")
        add_seat(self.member, self.org, self.term)
        self.s = Supplier.objects.create(organization=self.org, name="Caterer", contact_info="x")
        self.url = reverse("rating_submit", args=[self.org.pk, self.s.pk])
        self.page = reverse("supplier_detail", args=[self.org.pk, self.s.pk])

    def test_any_member_rates_and_the_supplier_page_shows_it(self):
        self.client.force_login(self.member)
        self.assertRedirects(self.client.post(self.url, {"score": "5", "comment": "Great"}), self.page)
        r = self.client.get(self.page)
        self.assertContains(r, "Great")
        self.assertContains(r, "5 / 5")
        self.assertEqual(r.context["average"], 5)

    def test_rating_again_replaces_your_own_never_pads(self):
        self.client.force_login(self.member)
        self.client.post(self.url, {"score": "5"})
        self.client.post(self.url, {"score": "2", "comment": "Changed my mind"})
        rating = SupplierRating.objects.get()
        self.assertEqual((rating.score, rating.comment), (2, "Changed my mind"))
        self.assertContains(self.client.get(self.page), "Change your rating")

    def test_bad_scores_and_long_comments_are_refused(self):
        self.client.force_login(self.member)
        for bad in ("0", "6", "x", ""):
            self.client.post(self.url, {"score": bad})
        self.client.post(self.url, {"score": "3", "comment": "a" * 1001})
        self.assertFalse(SupplierRating.objects.exists())

    def test_outsiders_and_closed_years_cannot_rate(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.post(self.url, {"score": "5"}).status_code, 404)
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.member)
        self.client.post(self.url, {"score": "5"})
        self.assertFalse(SupplierRating.objects.exists())
        self.assertNotContains(self.client.get(self.page), "Rate this supplier")

    def test_cannot_rate_another_organizations_supplier(self):
        org2, _, owner2 = make_org(name="Other")
        theirs = Supplier.objects.create(organization=org2, name="Theirs", contact_info="x")
        self.client.force_login(self.member)
        r = self.client.post(reverse("rating_submit", args=[self.org.pk, theirs.pk]), {"score": "5"})
        self.assertEqual(r.status_code, 404)
