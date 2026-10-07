"""Organizations: charter one, and look at one.

This slice owns only two things: creating an organization (with its first A.Y. and its founding
Executive) and the organization's own page. Committees, the roster and join codes each live in
their own slice and are linked from here.
"""
import re

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.accounts.models import Committee, Event, Membership, Organization, Term
from apps.shared.http import fail, json_login_required, read_json
from apps.shared.permissions import OrgRoleRequiredMixin
from apps.shared.selectors import ay_label
from apps.shared.years import ay_dates, parse_ay


@require_POST
@json_login_required
def create_view(request):
    """Home hook org:create. Body {name, acronym, academicYear}. Answers {url} of the new organization.

    The Organization, its first Term and the founder's EXECUTIVE seat are created together or not at all.
    """
    data = read_json(request)
    name = " ".join(str(data.get("name") or "").split())
    acronym = re.sub(r"[^A-Za-z0-9]", "", str(data.get("acronym") or "")).upper()
    years = parse_ay(str(data.get("academicYear") or ""))

    if not name:
        return fail("Give the organization a name.")
    if len(name) > 150:
        return fail("Keep the name under 150 characters.")
    if len(acronym) > 12:
        return fail("Keep the acronym to 12 letters or numbers.")
    if years is None:
        return fail("Enter the A.Y. as two years in a row, like 2026-2027.")
    if Organization.objects.filter(created_by=request.user, name__iexact=name).exists():
        return fail("You already created an organization with that name.", 409)

    start, end = ay_dates(years[0])
    with transaction.atomic():
        org = Organization.objects.create(name=name, acronym=acronym, created_by=request.user)
        term = Term.objects.create(organization=org, label=f"A.Y. {years[0]}-{years[1]}",
                                   start_date=start, end_date=end, status=Term.Status.ACTIVE)
        Membership.objects.create(user=request.user, organization=org, term=term, role=Membership.Role.EXECUTIVE,
                                  valid_from=start, valid_until=end)

    messages.success(request, f"{org.name} is ready. You are its Executive for {ay_label(term.label)}.")
    return JsonResponse({"url": reverse("organization_detail", args=[org.pk])}, status=201)


class OrganizationPage(OrgRoleRequiredMixin, TemplateView):
    """One organization: who you are in it, what A.Y. you are looking at, and the way into its other pages."""
    template_name = "organizations/organization.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access, org, term = self.access, self.access.organization, self.access.term

        seats = Membership.objects.filter(organization=org, term=term)

        # A glimpse for the overview: the next event if there is one, then the most recent ones. The events app owns the rest.
        today = timezone.localdate()
        events = Event.objects.filter(organization=org, term=term)
        glimpse = list(events.filter(date__gte=today).order_by("date", "pk")[:1])
        glimpse += list(events.filter(date__lt=today).order_by("-date", "-pk")[: 3 - len(glimpse)])

        years = list(org.terms.order_by("start_date", "pk"))
        context.update(
            ay=ay_label(term.label), recent_events=glimpse, today=today,
            founder=org.created_by,
            counts={
                "members": seats.values("user_id").distinct().count(),
                "committees": Committee.objects.filter(organization=org, is_active=True).count(),
                "events": events.count(),
            },
            years=[{"label": ay_label(t.label), "status": t.status, "is_this": t.pk == term.pk,
                    "dates": f"{t.start_date:%-d %b %Y} to {t.end_date:%-d %b %Y}"} for t in years],
            active_page="organization_detail",
        )
        return context