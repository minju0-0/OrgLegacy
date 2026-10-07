"""Join: redeeming a join code. Two steps, both called from the Home dialog.

  1. preview  - "You are about to join [Org] as [Role] in [Committee]. Confirm?"  (changes nothing)
  2. redeem   - creates the Membership on the organization's ACTIVE A.Y. and counts the use

A code stores no A.Y. (docs plan, section 2). The ACTIVE one is looked up here, at redemption. The redeem step
runs in a transaction that locks the code row, so two people racing for the last use cannot both get it, and a
database IntegrityError (a seat that was taken in the same instant) is answered, not crashed on.
"""
from django.contrib import messages
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.models import JoinCode, Membership
from apps.shared import codes
from apps.shared.http import fail, json_login_required, read_json
from apps.shared.notify import notify
from apps.shared.permissions import current_term
from apps.shared.selectors import ay_label

MAX_MISSES, WINDOW = 10, 600   # ten wrong codes in ten minutes, then wait


def _throttled(user):
    return cache.get(f"join-miss:{user.pk}", 0) >= MAX_MISSES


def _miss(user):
    key = f"join-miss:{user.pk}"
    cache.add(key, 0, WINDOW)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, WINDOW)


def seat_problem(user, code, term):
    """Why this person cannot take this seat, or None. Run again inside the redeem transaction."""
    org = code.organization.name
    held = Membership.objects.filter(user=user, organization=code.organization, term=term)
    leads = held.filter(role__in=[Membership.Role.EXECUTIVE, Membership.Role.COMMITTEE_HEAD]).exists()
    if code.role == JoinCode.Role.MEMBER:
        if leads:
            return f"You already lead {org} this A.Y., so you do not need a Member seat."
        if held.filter(role=Membership.Role.MEMBER, committee=code.committee).exists():
            return f"You already have this seat in {org}."
    else:
        if leads:
            return f"You already hold a leadership seat in {org} this A.Y."
        if Membership.objects.filter(organization=code.organization, term=term, committee=code.committee,
                                     role=Membership.Role.COMMITTEE_HEAD).exists():
            return f"{code.committee.name} already has a Committee Head this A.Y."
    return None


def _describe(code, term):
    role = code.get_role_display()
    where = f" in {code.committee.name}" if code.committee_id else ""
    return role, where


@require_POST
@json_login_required
def preview_view(request):
    """Home hook join:preview. Body {code}. Answers {summary, org, role, committee, ay} and changes nothing."""
    value = codes.normalize(read_json(request).get("code"))
    if not value:
        return fail("Enter all eight characters.")
    if _throttled(request.user):
        return fail("Too many wrong codes. Wait a few minutes and try again.", 429)
    code = JoinCode.objects.select_related("organization", "committee").filter(code=value).first()
    if code is None:
        _miss(request.user)
        return fail("That code is not valid.", 404)
    term = current_term(code.organization)
    problem = codes.redeem_problem(code, term) or seat_problem(request.user, code, term)
    if problem:
        return fail(problem, 409)
    role, where = _describe(code, term)
    ay = ay_label(term.label)
    return JsonResponse({
        "summary": f"You are about to join {code.organization.name} as {role}{where}, {ay}. Confirm?",
        "org": code.organization.name, "role": role, "committee": code.committee.name if code.committee_id else "", "ay": ay,
    })


@require_POST
@json_login_required
def redeem_view(request):
    """Home hook join:submit. Body {code}. Answers {url} of the organization the person just joined."""
    value = codes.normalize(read_json(request).get("code"))
    if not value:
        return fail("Enter all eight characters.")
    if _throttled(request.user):
        return fail("Too many wrong codes. Wait a few minutes and try again.", 429)

    try:
        with transaction.atomic():
            code = JoinCode.objects.select_for_update().filter(code=value).first()   # lock the row: no double redemption
            if code is None:
                _miss(request.user)
                return fail("That code is not valid.", 404)
            org = code.organization
            term = current_term(org)
            problem = codes.redeem_problem(code, term) or seat_problem(request.user, code, term)
            if problem:
                return fail(problem, 409)
            Membership.objects.create(user=request.user, organization=org, committee=code.committee, term=term,
                                      role=code.role, valid_from=term.start_date, valid_until=term.end_date)
            JoinCode.objects.filter(pk=code.pk).update(uses_count=F("uses_count") + 1)
    except IntegrityError:
        return fail("That seat was just taken by someone else. Ask an officer for a new code.", 409)

    role, where = _describe(code, term)
    who = request.user.get_full_name() or request.user.username
    if code.created_by_id != request.user.pk:
        notify([code.created_by], f"{who} joined {org.name} with your join code.", reverse("member_list", args=[org.pk]))
    messages.success(request, f"You joined {org.name} as {role}{where}.")
    return JsonResponse({"url": reverse("organization_detail", args=[org.pk])}, status=201)
