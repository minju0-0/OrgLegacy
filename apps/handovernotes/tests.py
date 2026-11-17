from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import HandoverNote, Membership, Notification, Term
from apps.shared.testing import add_seat, make_committee, make_org, make_user


class HandoverNotesTests(TestCase):
    def setUp(self):
        self.org, self.term, self.exec_user = make_org()
        self.comm = make_committee(self.org, name="Creatives")
        self.head_user = make_user("head_user")
        add_seat(self.head_user, self.org, self.term, role=Membership.Role.COMMITTEE_HEAD, committee=self.comm)
        self.member_user = make_user("member_user")
        add_seat(self.member_user, self.org, self.term, role=Membership.Role.MEMBER, committee=self.comm)
        self.outsider = make_user("outsider")

    def test_executive_creates_org_wide_note(self):
        self.client.force_login(self.exec_user)
        url = reverse("handover_add", args=[self.org.pk])
        resp = self.client.post(
            url,
            {"scope": HandoverNote.Scope.ORGANIZATION, "content": "Important financial handover lessons."},
        )
        self.assertEqual(resp.status_code, 302)
        note = HandoverNote.objects.get(organization=self.org)
        self.assertEqual(note.scope, HandoverNote.Scope.ORGANIZATION)
        self.assertIsNone(note.committee)
        self.assertEqual(note.author, self.exec_user)

    def test_executive_creates_committee_note(self):
        self.client.force_login(self.exec_user)
        url = reverse("handover_add", args=[self.org.pk])
        resp = self.client.post(
            url,
            {
                "scope": HandoverNote.Scope.COMMITTEE,
                "committee": self.comm.pk,
                "content": "Creatives guidelines for Canva teams.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = HandoverNote.objects.get(organization=self.org)
        self.assertEqual(note.scope, HandoverNote.Scope.COMMITTEE)
        self.assertEqual(note.committee, self.comm)

    def test_head_creates_committee_note_locked_to_own_committee(self):
        self.client.force_login(self.head_user)
        url = reverse("handover_add", args=[self.org.pk])
        # Even if someone tries to forge another committee, form locks to own committee
        other_comm = make_committee(self.org, name="Logistics")
        resp = self.client.post(
            url,
            {
                "scope": HandoverNote.Scope.COMMITTEE,
                "committee": other_comm.pk,
                "content": "Creatives assets folder on Google Drive.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = HandoverNote.objects.get(organization=self.org)
        self.assertEqual(note.scope, HandoverNote.Scope.COMMITTEE)
        self.assertEqual(note.committee, self.comm)  # Enforced to own committee!
        self.assertEqual(note.author, self.head_user)

    def test_member_cannot_create_note(self):
        self.client.force_login(self.member_user)
        url = reverse("handover_add", args=[self.org.pk])
        resp = self.client.post(
            url,
            {"scope": HandoverNote.Scope.COMMITTEE, "content": "Member trying to write note."},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(HandoverNote.objects.count(), 0)

    def test_any_member_can_view_notes_and_detail(self):
        note = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.exec_user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Read-only transition advice for all.",
        )
        self.client.force_login(self.member_user)
        list_url = reverse("handover_list", args=[self.org.pk])
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Read-only transition advice")

        detail_url = reverse("handover_detail", args=[self.org.pk, note.pk])
        resp2 = self.client.get(detail_url)
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "Read-only transition advice")

    def test_author_can_edit_own_note(self):
        note = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.exec_user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Original content.",
        )
        self.client.force_login(self.exec_user)
        url = reverse("handover_edit", args=[self.org.pk, note.pk])
        resp = self.client.post(
            url,
            {"scope": HandoverNote.Scope.ORGANIZATION, "content": "Updated content."},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.content, "Updated content.")

    def test_other_user_cannot_edit_note(self):
        note = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.exec_user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Original content.",
        )
        self.client.force_login(self.head_user)
        url = reverse("handover_edit", args=[self.org.pk, note.pk])
        resp = self.client.post(
            url,
            {"scope": HandoverNote.Scope.ORGANIZATION, "content": "Head trying to tamper."},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.content, "Original content.")

    def test_author_and_executive_can_delete_note(self):
        note1 = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.head_user,
            scope=HandoverNote.Scope.COMMITTEE,
            committee=self.comm,
            content="Head note.",
        )
        # Head deletes own note
        self.client.force_login(self.head_user)
        del_url = reverse("handover_delete", args=[self.org.pk, note1.pk])
        resp = self.client.post(del_url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(HandoverNote.objects.filter(pk=note1.pk).exists())

        # Executive deletes another note
        note2 = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.head_user,
            scope=HandoverNote.Scope.COMMITTEE,
            committee=self.comm,
            content="Another note.",
        )
        self.client.force_login(self.exec_user)
        del_url2 = reverse("handover_delete", args=[self.org.pk, note2.pk])
        resp2 = self.client.post(del_url2)
        self.assertEqual(resp2.status_code, 302)
        self.assertFalse(HandoverNote.objects.filter(pk=note2.pk).exists())

    def test_closed_term_is_read_only(self):
        self.term.status = Term.Status.CLOSED
        self.term.save()
        self.client.force_login(self.exec_user)
        url = reverse("handover_add", args=[self.org.pk])
        resp = self.client.post(
            url,
            {"scope": HandoverNote.Scope.ORGANIZATION, "content": "Post-closing attempt."},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("organization_detail", args=[self.org.pk]))
        self.assertEqual(HandoverNote.objects.count(), 0)

    def test_outsider_gets_404(self):
        self.client.force_login(self.outsider)
        url = reverse("handover_list", args=[self.org.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_invalid_edit_preserves_saved_note_on_page(self):
        note = HandoverNote.objects.create(
            organization=self.org,
            term=self.term,
            author=self.exec_user,
            scope=HandoverNote.Scope.ORGANIZATION,
            content="Saved prose stays visible.",
        )
        self.client.force_login(self.exec_user)
        resp = self.client.post(
            reverse("handover_edit", args=[self.org.pk, note.pk]),
            {"scope": HandoverNote.Scope.ORGANIZATION, "content": "   "},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Saved prose stays visible.", status_code=400)
        self.assertContains(resp, "data-open-on-load", status_code=400)
