"""Members: who holds a seat this A.Y., leaving, and removing someone.

Joining is the `join` slice (a seat is only ever created from a join code, or at founding and term succession).
This slice owns the roster and the two ways a seat ends. Both end only the seat in the ACTIVE A.Y.: seats in
closed A.Y.s are archived records and are never deleted.
"""
from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Membership, Term
from apps.shared.http import fail, wants_json
from apps.shared.notify import notify
from apps.shared.permissions import EXECUTIVE, OrgRoleRequiredMixin
from apps.shared.selectors import ay_label


class MemberList(OrgRoleRequiredMixin, TemplateView):
    template_name = "members/members.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        order = Case(When(role="EXECUTIVE", then=Value(0)), When(role="COMMITTEE_HEAD", then=Value(1)),
                     default=Value(2), output_field=IntegerField())
        seats = (Membership.objects.filter(organization=access.organization, term=access.term)
                 .select_related("user", "committee").annotate(rank=order)
                 .order_by("rank", "committee__name", "user__first_name", "user__username"))
        others_exec = Membership.objects.filter(organization=access.organization, term=access.term,
                                                role=EXECUTIVE).exclude(user=self.request.user).exists()
        context.update(
            ay=ay_label(access.term.label), seats=seats, active_page="member_list",
            can_remove=access.is_executive and access.is_open,
            can_leave=access.term.status in (Term.Status.ACTIVE, Term.Status.PENDING_SIGNOFF),
            sole_executive=access.is_executive and not others_exec,
            headcount=len({s.user_id for s in seats}),
        )
        return context


class LeaveView(OrgRoleRequiredMixin, View):
    """Home hook org:leave-confirm (JSON) and the Leave button on the roster (form post). Ends your seats in the live A.Y."""
    json = False

    def dispatch(self, request, *args, **kwargs):
        self.json = wants_json(request)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, org_id):
        access = self.access
        if access.term.status not in (Term.Status.ACTIVE, Term.Status.PENDING_SIGNOFF):
            return self.stop("Your seat in this organization is in a closed A.Y., which stays on the record. There is nothing to leave.", 409)
        if access.is_executive and not Membership.objects.filter(
                organization=access.organization, term=access.term, role=EXECUTIVE).exclude(user=request.user).exists():
            return self.stop("You are the only Executive. An organization cannot be left without one, so hand over before you leave.", 409)

        name = access.organization.name
        officers = list(Membership.objects.filter(organization=access.organization, term=access.term, role=EXECUTIVE)
                        .exclude(user=request.user).select_related("user"))
        Membership.objects.filter(user=request.user, organization=access.organization, term=access.term).delete()
        who = request.user.get_full_name() or request.user.username
        notify([m.user for m in officers], f"{who} left {name}.",
               reverse("member_list", args=[access.organization.pk]))

        messages.success(request, f"You left {name}. To come back you will need a new join code.")
        if self.json:
            return JsonResponse({"url": reverse("home")})
        return redirect("home")

    def stop(self, message, status):
        if self.json:
            return fail(message, status)
        messages.error(self.request, message)
        return redirect(reverse("member_list", args=[self.access.organization.pk]))


class RemoveView(OrgRoleRequiredMixin, View):
    """An Executive removes someone's seat in the ACTIVE A.Y. This is how a leaked join code is cleaned up."""
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id, membership_id):
        access = self.access
        seat = get_object_or_404(Membership.objects.select_related("user"), pk=membership_id,
                                 organization=access.organization, term=access.term)
        back = redirect(reverse("member_list", args=[access.organization.pk]))
        if seat.user_id == request.user.pk:
            messages.error(request, "Use Leave organization to end your own seat.")
            return back
        if seat.role == EXECUTIVE:
            messages.error(request, "Executives cannot be removed here. Executive seats change only when an A.Y. is handed over.")
            return back

        who = seat.user.get_full_name() or seat.user.username
        user, org = seat.user, access.organization
        seat.delete()
        if not Membership.objects.filter(user=user, organization=org, term=access.term).exists():
            notify([user], f"You were removed from {org.name}.", reverse("home"))
        messages.success(request, f"{who} was removed from {org.name}.")
        return back
