"""Handover Notes: transition documentation written by outgoing officers for the next set.

Executives write organization-wide notes; Committee Heads write notes for their own committee.
All members of the organization can read notes of the active A.Y. (and past archived A.Y.s they served in).
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import HandoverNote, Membership, Term
from apps.shared.notify import notify
from apps.shared.permissions import EXECUTIVE, HEAD, LIVE, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import HandoverNoteForm

WRITERS = (EXECUTIVE, HEAD)


def base_context(access, **extra):
    context = {
        "access": access,
        "organization": access.organization,
        "term": access.term,
        "ay": ay_label(access.term.label),
        "org_nav": org_nav(access),
        "active_page": "handover_list",
        "can_add": access.is_open and access.role in WRITERS,
    }
    context.update(extra)
    return context


def term_notes(access):
    return (
        HandoverNote.objects.filter(organization=access.organization, term=access.term)
        .select_related("author", "committee", "term")
        .order_by("-created_at", "-pk")
    )


def readable_notes(access, user):
    """Handover notes this member can open: current A.Y. plus closed archive A.Y.s for live members, or served A.Y.s for alumni."""
    qs = HandoverNote.objects.filter(organization=access.organization).select_related("author", "committee", "term")
    if access.term.status in LIVE:
        return qs.filter(Q(term=access.term) | Q(term__status=Term.Status.CLOSED))
    served = Membership.objects.filter(user=user, organization=access.organization).values("term_id")
    return qs.filter(term_id__in=served)


class NoteList(OrgRoleRequiredMixin, TemplateView):
    template_name = "handovernotes/handover_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        notes = list(term_notes(access))
        org_notes = [n for n in notes if n.scope == HandoverNote.Scope.ORGANIZATION]
        comm_notes = [n for n in notes if n.scope == HandoverNote.Scope.COMMITTEE]

        context.update(
            base_context(
                access,
                notes=notes,
                org_notes=org_notes,
                comm_notes=comm_notes,
                total_count=len(notes),
            )
        )
        if context["can_add"]:
            context["form"] = HandoverNoteForm(access=access)
        return context


class NoteDetail(OrgRoleRequiredMixin, TemplateView):
    template_name = "handovernotes/handover_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        note = get_object_or_404(
            readable_notes(access, self.request.user),
            pk=self.kwargs["pk"],
        )
        is_open_note_term = (note.term_id == access.term.pk and access.is_open)
        can_edit = is_open_note_term and note.author_id == self.request.user.pk
        can_delete = is_open_note_term and (
            note.author_id == self.request.user.pk or access.is_executive
        )
        context.update(
            base_context(
                access,
                note=note,
                term=note.term,
                ay=ay_label(note.term.label),
                can_edit=can_edit,
                can_delete=can_delete,
                edit_form=HandoverNoteForm(instance=note, access=access) if can_edit else None,
            )
        )
        return context


class NoteCreate(OrgRoleRequiredMixin, View):
    allowed_roles = WRITERS
    require_open_term = True

    def get(self, request, org_id):
        return redirect(reverse("handover_list", args=[self.access.organization.pk]))

    def post(self, request, org_id):
        access = self.access
        form = HandoverNoteForm(request.POST, access=access)
        if not form.is_valid():
            notes = list(term_notes(access))
            context = base_context(
                access,
                notes=notes,
                org_notes=[n for n in notes if n.scope == HandoverNote.Scope.ORGANIZATION],
                comm_notes=[n for n in notes if n.scope == HandoverNote.Scope.COMMITTEE],
                total_count=len(notes),
                form=form,
                open_dialog="handover-add-modal",
            )
            return render(request, "handovernotes/handover_list.html", context, status=400)

        note = form.save(commit=False)
        note.organization = access.organization
        note.term = access.term
        note.author = request.user
        note.save()

        # Notify other executives and committee peers
        who = request.user.get_full_name() or request.user.username
        recipients_qs = Membership.objects.filter(
            organization=access.organization, term=access.term
        ).exclude(user=request.user)

        if note.scope == HandoverNote.Scope.COMMITTEE and note.committee:
            recipients = [
                m.user
                for m in recipients_qs.filter(committee=note.committee).select_related("user")
            ]
            scope_desc = f"{note.committee.name} committee"
        else:
            recipients = [
                m.user
                for m in recipients_qs.filter(role=EXECUTIVE).select_related("user")
            ]
            scope_desc = "organization-wide"

        notify(
            recipients,
            f"{who} filed a {scope_desc} handover note.",
            reverse("handover_detail", args=[access.organization.pk, note.pk]),
        )
        messages.success(request, "Your handover note was saved.")
        return redirect(reverse("handover_detail", args=[access.organization.pk, note.pk]))


class NoteEdit(OrgRoleRequiredMixin, View):
    require_open_term = True

    def get(self, request, org_id, pk):
        return redirect(reverse("handover_detail", args=[self.access.organization.pk, pk]))

    def post(self, request, org_id, pk):
        access = self.access
        note = get_object_or_404(
            HandoverNote, pk=pk, organization=access.organization, term=access.term
        )
        if note.author_id != request.user.pk:
            messages.error(request, "You can only edit your own handover notes.")
            return redirect(reverse("handover_detail", args=[access.organization.pk, pk]))

        form = HandoverNoteForm(request.POST, instance=note, access=access)
        if not form.is_valid():
            note = get_object_or_404(
                HandoverNote.objects.select_related("author", "committee", "term"),
                pk=pk, organization=access.organization, term=access.term
            )
            can_edit = True
            can_delete = access.is_open and (
                note.author_id == request.user.pk or access.is_executive
            )
            context = base_context(
                access,
                note=note,
                term=note.term,
                ay=ay_label(note.term.label),
                can_edit=can_edit,
                can_delete=can_delete,
                edit_form=form,
                open_dialog="handover-edit-modal",
            )
            return render(request, "handovernotes/handover_detail.html", context, status=400)

        form.save()
        messages.success(request, "Your handover note was updated.")
        return redirect(reverse("handover_detail", args=[access.organization.pk, pk]))


class NoteDelete(OrgRoleRequiredMixin, View):
    require_open_term = True

    def get(self, request, org_id, pk):
        return redirect(reverse("handover_detail", args=[self.access.organization.pk, pk]))

    def post(self, request, org_id, pk):
        access = self.access
        note = get_object_or_404(
            HandoverNote, pk=pk, organization=access.organization, term=access.term
        )
        if not (note.author_id == request.user.pk or access.is_executive):
            messages.error(request, "You do not have permission to delete this note.")
            return redirect(reverse("handover_detail", args=[access.organization.pk, pk]))

        note.delete()
        messages.success(request, "The handover note was deleted.")
        return redirect(reverse("handover_list", args=[access.organization.pk]))
