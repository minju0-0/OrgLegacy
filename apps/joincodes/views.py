"""Join codes: the issuing side. Executives and Committee Heads make and cancel codes; redeeming one is the `join` slice.

Who may make what is decided in JoinCodeForm. Cancelling: the person who made a code, or any current Executive.
"""
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.accounts.models import JoinCode
from apps.shared import codes
from apps.shared.permissions import EXECUTIVE, HEAD, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import JoinCodeForm

TEMPLATE = "joincodes/joincodes.html"
ISSUERS = (EXECUTIVE, HEAD)


def visible_codes(access):
    qs = JoinCode.objects.filter(organization=access.organization).select_related("committee", "created_by")
    if access.is_head:
        qs = qs.filter(committee=access.committee)
    return qs.order_by("-pk")[:100]


def code_rows(access, user):
    now = timezone.now()
    rows = []
    for c in visible_codes(access):
        s = codes.state(c, now)
        rows.append({
            "id": c.pk, "raw": c.code, "pretty": codes.pretty(c.code), "role": c.get_role_display(), "role_code": c.role,
            "committee": c.committee.name if c.committee else "", "uses": c.uses_count, "max": c.max_uses,
            "expires": timezone.localtime(c.expires_at).strftime("%-d %b, %-I:%M %p"),
            "state": s, "state_label": codes.STATE_LABEL[s], "live": s == "active",
            "by": c.created_by.get_full_name() or c.created_by.username, "mine": c.created_by_id == user.pk,
            "can_revoke": s == "active" and (access.is_executive or c.created_by_id == user.pk) and access.is_open,
        })
    rows.sort(key=lambda r: not r["live"])     # live first; the rest keep newest-first order
    return rows


class PageContext:
    def page(self, request, **extra):
        access = self.access
        context = {
            "access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
            "codes": code_rows(access, request.user), "form": JoinCodeForm(access=access),
            "can_create": access.is_open, "org_nav": org_nav(access), "active_page": "joincode_list",
            "head_hours": ",".join(str(h) for h in codes.HEAD_EXPIRY_HOURS),
            "member_hours": ",".join(str(h) for h in codes.MEMBER_EXPIRY_HOURS),
        }
        context.update(extra)
        return context


class JoinCodeList(OrgRoleRequiredMixin, PageContext, View):
    allowed_roles = ISSUERS

    def get(self, request, org_id):
        return render(request, TEMPLATE, self.page(request))


class JoinCodeCreate(OrgRoleRequiredMixin, PageContext, View):
    allowed_roles = ISSUERS
    require_open_term = True

    def post(self, request, org_id):
        form = JoinCodeForm(request.POST, access=self.access)
        if not form.is_valid():
            return render(request, TEMPLATE, self.page(request, form=form, open_dialog="joincode-modal"), status=400)
        data = form.cleaned_data
        code = JoinCode.objects.create(
            code=codes.new_code_value(), organization=self.access.organization, committee=data.get("committee"),
            role=data["role"], max_uses=data["max_uses"], created_by=request.user,
            expires_at=codes.expiry_from_hours(data["hours"]),
        )
        where = f" for {code.committee.name}" if code.committee else ""
        messages.success(request, f"Join code {codes.pretty(code.code)} is ready{where}.")
        return redirect(reverse("joincode_list", args=[self.access.organization.pk]))


class JoinCodeRevoke(OrgRoleRequiredMixin, View):
    allowed_roles = ISSUERS
    require_open_term = True

    def post(self, request, org_id, pk):
        code = get_object_or_404(JoinCode, pk=pk, organization=self.access.organization)
        back = redirect(reverse("joincode_list", args=[self.access.organization.pk]))
        if not (self.access.is_executive or code.created_by_id == request.user.pk):
            messages.error(request, "Only the person who made a code, or an Executive, can cancel it.")
            return back
        if not code.revoked_at:
            code.revoked_at = timezone.now()
            code.save(update_fields=["revoked_at"])
        messages.success(request, f"Join code {codes.pretty(code.code)} was cancelled. It can no longer be used.")
        return back


class JoinCodeQuick(OrgRoleRequiredMixin, View):
    """Home hook share:regenerate. A fresh cross-committee Member code, and your earlier ones are cancelled.

    Replacing rather than piling up keeps one live code per Executive, so an old one that leaked stops working.
    """
    allowed_roles = (EXECUTIVE,)
    require_open_term = True
    json = True

    def post(self, request, org_id):
        org = self.access.organization
        with transaction.atomic():
            JoinCode.objects.filter(organization=org, created_by=request.user, committee__isnull=True,
                                    role=JoinCode.Role.MEMBER, revoked_at__isnull=True).update(revoked_at=timezone.now())
            code = JoinCode.objects.create(code=codes.new_code_value(), organization=org, committee=None,
                                           role=JoinCode.Role.MEMBER, max_uses=codes.QUICK_USES, created_by=request.user,
                                           expires_at=codes.expiry_from_hours(codes.QUICK_HOURS))
        return JsonResponse({"code": code.code, "expires": codes.expires_text(code)}, status=201)
