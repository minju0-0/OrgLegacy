"""Who may do what inside an organization.

A person's role lives on their Membership, per organization and per A.Y. (docs plan, section 3). Every
organization-scoped page resolves the person's seat through `resolve_access` and checks it with
`OrgRoleRequiredMixin`, so no view re-implements the rules.

Rules baked in here:
  * Not a member (or no such organization): 404. There is no public directory, so we never confirm it exists.
  * The A.Y. a page works on is the live one when the person has a seat in it, otherwise the latest A.Y. they served in.
  * Only an ACTIVE A.Y. can be changed. PENDING_SIGNOFF is under review and CLOSED is the archive: both read-only.
  * A person with several seats in one A.Y. acts with the highest.
"""
from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from apps.accounts.models import Membership, Organization, Term

from .http import fail

EXECUTIVE = Membership.Role.EXECUTIVE
HEAD = Membership.Role.COMMITTEE_HEAD
MEMBER = Membership.Role.MEMBER

RANK = {MEMBER: 0, HEAD: 1, EXECUTIVE: 2}
LIVE = (Term.Status.ACTIVE, Term.Status.PENDING_SIGNOFF)


@dataclass
class OrgAccess:
    organization: Organization
    term: Term
    seat: Membership          # the person's highest seat in `term`
    seats: list               # all of their seats in `term`

    @property
    def role(self):
        return self.seat.role

    @property
    def committee(self):
        return self.seat.committee

    @property
    def committee_id(self):
        return self.seat.committee_id

    @property
    def is_open(self):
        """True only while the A.Y. is ACTIVE. Everything that writes requires this."""
        return self.term.status == Term.Status.ACTIVE

    @property
    def is_executive(self):
        return self.role == EXECUTIVE

    @property
    def is_head(self):
        return self.role == HEAD

    @property
    def can_issue_codes(self):
        return self.is_open and self.role in (EXECUTIVE, HEAD)


def resolve_access(user, org_id):
    """The person's OrgAccess for this organization, or None if they have no seat in it."""
    seats = list(Membership.objects.filter(user=user, organization_id=org_id)
                 .select_related("organization", "term", "committee"))
    if not seats:
        return None
    live = [s for s in seats if s.term.status in LIVE]
    anchor = live[0] if live else max(seats, key=lambda s: (s.term.start_date, s.term_id))
    in_term = [s for s in seats if s.term_id == anchor.term_id]
    best = max(in_term, key=lambda s: RANK.get(s.role, -1))
    return OrgAccess(organization=best.organization, term=best.term, seat=best, seats=in_term)


def current_term(organization):
    """The ACTIVE term of an organization, or None. Used by redemption and any 'new seat' flow."""
    return Term.objects.filter(organization=organization, status=Term.Status.ACTIVE).first()


def org_nav(access):
    """Context for the sidebar's organization group (templates/shared/shell/_sidebar.html)."""
    org = access.organization
    return {"id": org.pk, "name": org.name, "label": org.acronym or org.name,
            "can_issue_codes": access.role in (EXECUTIVE, HEAD)}


class OrgRoleRequiredMixin:
    """Put first in the bases of a View. Resolves `self.access` from the `org_id` URL argument.

        class Roster(OrgRoleRequiredMixin, TemplateView): ...                       any member
        class Add(OrgRoleRequiredMixin, View):
            allowed_roles = (EXECUTIVE,); require_open_term = True; json = True      executives, ACTIVE A.Y. only
    """
    allowed_roles = None          # None = any member; otherwise a tuple of Membership.Role values
    require_open_term = False     # True for anything that writes
    json = False                  # True for endpoints called from script: answer JSON, not a redirect
    org_kwarg = "org_id"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            if self.json:
                return fail("Log in again to continue.", 401)
            return redirect_to_login(request.get_full_path())
        access = resolve_access(request.user, kwargs[self.org_kwarg])
        if access is None:
            if self.json:
                return fail("That organization could not be found.", 404)
            raise Http404("No such organization.")
        self.access = request.access = access
        if self.allowed_roles is not None and access.role not in self.allowed_roles:
            return self.refuse("You do not have permission to do that.", 403)
        if self.require_open_term and not access.is_open:
            why = ("This A.Y. is awaiting approval, so it cannot be changed."
                   if access.term.status == Term.Status.PENDING_SIGNOFF
                   else "This A.Y. is closed, so it cannot be changed.")
            return self.refuse(why, 409)
        return View.dispatch(self, request, *args, **kwargs)

    def refuse(self, message, status):
        if self.json:
            return fail(message, status)
        if status == 403:
            raise PermissionDenied(message)
        messages.info(self.request, message)
        return redirect(reverse("organization_detail", args=[self.access.organization.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(access=self.access, organization=self.access.organization,
                       term=self.access.term, org_nav=org_nav(self.access))
        return context
