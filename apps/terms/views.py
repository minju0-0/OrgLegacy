"""Terms: set up the next A.Y. while the current one is live. Executives only.

This slice owns one thing: the next A.Y.'s name and dates (a TermPlan on the current term). It does not close
anything. The nominee slate, the sign-off vote and the switch to the new A.Y. are Phase 6. Until then the plan is
simply what the organization intends, shown read-only on the overview.

  Only an ACTIVE A.Y. can be planned. Once it is awaiting approval the plan is locked with it.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.accounts.models import TermPlan
from apps.shared.notify import notify
from apps.shared.permissions import EXECUTIVE, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import PlanForm


def page(request, access, form=None, status=200):
    plan = TermPlan.objects.filter(term=access.term).first()
    if form is None:
        form = PlanForm(initial=PlanForm.suggestion(access.term, plan), term=access.term)
    context = {"access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
               "org_nav": org_nav(access), "active_page": "term_plan", "plan": plan, "form": form,
               "can_plan": access.is_open}
    return render(request, "terms/plan.html", context, status=status)


class PlanPage(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)

    def get(self, request, org_id):
        return page(request, self.access)


class PlanSave(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id):
        access = self.access
        form = PlanForm(request.POST, term=access.term)
        if not form.is_valid():
            return page(request, access, form, status=400)
        data = form.cleaned_data
        existed = TermPlan.objects.filter(term=access.term).exists()
        TermPlan.objects.update_or_create(term=access.term, defaults={
            "label": form.label, "start_date": data["start_date"], "end_date": data["end_date"], "created_by": request.user})
        others = [m.user for m in access.organization.memberships.filter(term=access.term, role=EXECUTIVE)
                  .exclude(user=request.user).select_related("user")]
        who = request.user.get_full_name() or request.user.username
        notify(others, f"{who} {'changed' if existed else 'set up'} the next A.Y. for {access.organization.name}: {form.label}.",
               reverse("term_plan", args=[access.organization.pk]))
        messages.success(request, f"{form.label} is set up as the next A.Y.")
        return redirect(reverse("term_plan", args=[access.organization.pk]))


class PlanClear(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id):
        deleted, _ = TermPlan.objects.filter(term=self.access.term).delete()
        if deleted:
            messages.success(request, "The next A.Y. plan was cleared.")
        return redirect(reverse("term_plan", args=[self.access.organization.pk]))
