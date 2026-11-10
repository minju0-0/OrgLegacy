from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Committee, JoinCode, Membership, Term
from apps.shared.testing import add_seat, make_code, make_committee, make_org, make_user


class CommitteeTests(TestCase):
    def setUp(self):
        self.org, self.term, self.owner = make_org()
        self.member = make_user()
        add_seat(self.member, self.org, self.term)
        self.list = reverse("committee_list", args=[self.org.pk])
        self.add = reverse("committee_create", args=[self.org.pk])

    def test_any_member_can_read_but_only_executives_see_controls(self):
        make_committee(self.org)
        self.client.force_login(self.member)
        r = self.client.get(self.list)
        self.assertContains(r, "Logistics")
        self.assertNotContains(r, "Add a committee")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.list), "Add a committee")

    def test_executive_adds_a_committee(self):
        self.client.force_login(self.owner)
        r = self.client.post(self.add, {"add-name": "  Creative   Team "})
        self.assertRedirects(r, self.list)
        self.assertEqual(Committee.objects.get().name, "Creative Team")

    def test_member_cannot_add(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(self.add, {"add-name": "Nope"}).status_code, 403)
        self.assertFalse(Committee.objects.exists())

    def test_duplicate_name_is_refused_inside_the_dialog(self):
        make_committee(self.org, "Logistics")
        self.client.force_login(self.owner)
        r = self.client.post(self.add, {"add-name": "logistics"})
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "already has a committee with that name", status_code=400)
        self.assertContains(r, "data-open-on-load", status_code=400)
        self.assertEqual(Committee.objects.count(), 1)

    def test_rename_allows_own_name_and_refuses_anothers(self):
        a, b = make_committee(self.org, "A"), make_committee(self.org, "B")
        self.client.force_login(self.owner)
        url = reverse("committee_rename", args=[self.org.pk, a.pk])
        self.assertEqual(self.client.post(url, {"rename-name": "B"}).status_code, 400)
        self.assertRedirects(self.client.post(url, {"rename-name": "a"}), self.list)
        a.refresh_from_db()
        self.assertEqual(a.name, "a")

    def test_deactivate_keeps_members_and_cancels_codes_then_reactivates(self):
        c = make_committee(self.org)
        add_seat(self.member, self.org, self.term, committee=c)
        code = make_code(self.org, self.owner, committee=c)
        self.client.force_login(self.owner)
        url = reverse("committee_toggle", args=[self.org.pk, c.pk])
        self.client.post(url)
        c.refresh_from_db(); code.refresh_from_db()
        self.assertFalse(c.is_active)
        self.assertIsNotNone(code.revoked_at)
        self.assertEqual(Membership.objects.filter(committee=c).count(), 1)
        self.client.post(url)
        c.refresh_from_db()
        self.assertTrue(c.is_active)

    def test_cannot_touch_another_organizations_committee(self):
        other, _, other_owner = make_org(name="Other")
        theirs = make_committee(other)
        self.client.force_login(self.owner)
        r = self.client.post(reverse("committee_toggle", args=[self.org.pk, theirs.pk]))
        self.assertEqual(r.status_code, 404)

    def test_closed_year_blocks_changes(self):
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.owner)
        r = self.client.post(self.add, {"add-name": "Late"})
        self.assertRedirects(r, reverse("organization_detail", args=[self.org.pk]))
        self.assertFalse(Committee.objects.exists())
