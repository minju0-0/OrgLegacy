"""Committees: the divisions of an organization. Everyone in it can read the list; only Executives change it.

Deactivating is a soft delete (docs plan, section 3): the committee and everything logged under it stay in
the record, it just stops taking new people. Its unused join codes are cancelled so nobody can still join it.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Committee, JoinCode, Membership
from apps.shared.permissions import EXECUTIVE, HEAD, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import CommitteeForm

TEMPLATE = "committees/committees.html"


def committee_rows(access):
    org, term = access.organization, access.term
    seats = (Membership.objects.filter(organization=org, term=term, committee__isnull=False).select_related("user"))
    by_committee = {}
    for seat in seats:
        by_committee.setdefault(seat.committee_id, []).append(seat)
    rows = []
    for c in Committee.objects.filter(organization=org).order_by("-is_active", "name"):
        group = by_committee.get(c.pk, [])
        rows.append({
            "id": c.pk, "name": c.name, "active": c.is_active,
            "head": next((s.user for s in group if s.role == HEAD), None),
            "size": len({s.user_id for s in group}),
        })
    return rows


class PageContext:
    """Context shared by the list and by the three forms that re-draw it when they find a mistake."""

    def page(self, request, **extra):
        access = self.access
        context = {
            "access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
            "committees": committee_rows(access), "can_edit": access.is_executive and access.is_open,
            "add_form": CommitteeForm(organization=access.organization, prefix="add"),
            "rename_form": CommitteeForm(organization=access.organization, prefix="rename"),
            "active_page": "committee_list",
            "org_nav": org_nav(access),
        }
        context.update(extra)
        return context


class CommitteeList(OrgRoleRequiredMixin, PageContext, View):
    def get(self, request, org_id):
        return render(request, TEMPLATE, self.page(request))


class CommitteeWrite(OrgRoleRequiredMixin, PageContext, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def back(self):
        return redirect(reverse("committee_list", args=[self.access.organization.pk]))


class CommitteeCreate(CommitteeWrite):
    def post(self, request, org_id):
        form = CommitteeForm(request.POST, organization=self.access.organization, prefix="add")
        if not form.is_valid():
            return render(request, TEMPLATE, self.page(request, add_form=form, open_dialog="committee-add-modal"), status=400)
        committee = Committee.objects.create(organization=self.access.organization, name=form.cleaned_data["name"])
        messages.success(request, f"{committee.name} is now a committee.")
        return self.back()


class CommitteeRename(CommitteeWrite):
    def post(self, request, org_id, pk):
        committee = get_object_or_404(Committee, pk=pk, organization=self.access.organization)
        form = CommitteeForm(request.POST, organization=self.access.organization, instance=committee, prefix="rename")
        if not form.is_valid():
            return render(request, TEMPLATE, self.page(
                request, rename_form=form, rename_target=committee, open_dialog="committee-rename-modal"), status=400)
        old, committee.name = committee.name, form.cleaned_data["name"]
        committee.save(update_fields=["name"])
        messages.success(request, f"{old} is now called {committee.name}.")
        return self.back()


class CommitteeToggle(CommitteeWrite):
    """Deactivate an active committee, or bring an inactive one back."""

    def post(self, request, org_id, pk):
        committee = get_object_or_404(Committee, pk=pk, organization=self.access.organization)
        if committee.is_active:
            committee.is_active = False
            committee.save(update_fields=["is_active"])
            cancelled = JoinCode.objects.filter(committee=committee, revoked_at__isnull=True).update(revoked_at=timezone.now())
            extra = " Its join codes were cancelled." if cancelled else ""
            messages.success(request, f"{committee.name} is now inactive. Its records stay.{extra}")
        else:
            committee.is_active = True
            committee.save(update_fields=["is_active"])
            messages.success(request, f"{committee.name} is active again.")
        return self.back()
