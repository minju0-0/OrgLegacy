"""Read-side queries shared by the Home and Profile slices.

Both pages describe the same thing: the places a user holds a seat. A seat is a
Membership (user + organization + term + role). Each record returned here is a
plain dict so templates stay free of ORM details.
"""
import re
from datetime import timedelta

from django.db.models import Count, F
from django.urls import reverse
from django.utils import timezone
from django.utils.timesince import timesince

from apps.accounts.models import (
    Event,
    HandoverNote,
    JoinCode,
    Membership,
    Supplier,
    Term,
    TermPlan,
    TermSignOff,
)

from . import codes

LIVE_STATUSES = (Term.Status.ACTIVE, Term.Status.PENDING_SIGNOFF)


def ay_label(label):
    """'2026-2027' or 'A.Y. 2026-2027' -> 'A.Y. 2026-2027'. One spelling everywhere: full years, plain hyphen."""
    text = re.sub(r"^\s*A\.?\s*Y\.?\s*", "", label or "", flags=re.I).strip()
    text = re.sub(r"(?<=\d)\s*[-\u2013\u2014]\s*(?=\d)", "-", text)
    return f"A.Y. {text}" if text else "A.Y."


def _records(memberships):
    """Turn Membership rows into template-ready dicts, adding headcount and a few faces per term."""
    memberships = list(memberships)
    term_ids = {m.term_id for m in memberships}

    faces = {}
    if term_ids:
        peers = (Membership.objects.filter(term_id__in=term_ids)
                 .select_related("user").order_by("created_at", "pk"))
        for peer in peers:
            bucket = faces.setdefault(peer.term_id, {})
            bucket.setdefault(peer.user_id, peer.user)   # one face per person, even with two seats

    out = []
    for m in memberships:
        people = list(faces.get(m.term_id, {}).values())
        out.append({
            "id": m.organization_id,       # the organization, so data-org="..." hooks receive an organization id
            "seat_id": m.pk,
            "name": m.organization.name,
            "acronym": m.organization.acronym,
            "role": m.get_role_display(),
            "role_code": m.role,
            "title": m.title,
            "committee": m.committee.name if m.committee else "",
            "ay": ay_label(m.term.label),
            "status": m.term.status,
            "member_count": len(people),
            "members": people[:3],
            "url": reverse("organization_detail", args=[m.organization_id]),
        })
    return out


def _base(user):
    return (Membership.objects.filter(user=user)
            .select_related("organization", "committee", "term"))


def memberships_for_profile(user):
    """Every seat the user has held, newest A.Y. first. Powers the Profile ledger."""
    return _records(_base(user).order_by("-term__start_date", "organization__name", "pk"))


def _ago(moment):
    """'Just now', '2 hours ago', '3 days ago'. One unit, like the rest of the interface."""
    if timezone.now() - moment < timedelta(minutes=1):
        return "Just now"
    return timesince(moment).split(",")[0].replace("\xa0", " ") + " ago"


def share_codes(org_ids):
    """{organization_id: newest code anyone can still redeem as a cross-committee Member}. Feeds the Home share dialog."""
    now = timezone.now()
    found = {}
    rows = (JoinCode.objects.filter(organization_id__in=org_ids, committee__isnull=True, role=JoinCode.Role.MEMBER,
                                    revoked_at__isnull=True, expires_at__gt=now, uses_count__lt=F("max_uses"))
            .order_by("-pk"))
    for row in rows:
        found.setdefault(row.organization_id, row)
    return found


def organizations_for_home(user):
    """One card per organization: the user's live seat if they have one, else their latest.

    A person can hold two seats in one A.Y. (a committee seat and an executive seat);
    the highest role wins the card. Live organizations sort before closed ones.
    Executives of an ACTIVE A.Y. also get the share-a-code fields the Home dialog reads.
    """
    rank = {"EXECUTIVE": 0, "COMMITTEE_HEAD": 1, "MEMBER": 2}
    best = {}
    for m in _base(user).order_by("-term__start_date", "pk"):
        live = m.term.status in LIVE_STATUSES
        key = (not live, -m.term.start_date.toordinal(), rank.get(m.role, 3))
        cur = best.get(m.organization_id)
        if cur is None or key < cur[0]:
            best[m.organization_id] = (key, m)
    chosen = [m for _, m in sorted(best.values(), key=lambda kv: (kv[0][0], kv[1].organization.name.lower()))]
    records = _records(chosen)

    # Real counts for the card: events and notes of the A.Y. the card shows, suppliers of the organization.
    term_ids, org_ids = [m.term_id for m in chosen], [m.organization_id for m in chosen]
    events = dict(Event.objects.filter(term_id__in=term_ids).values_list("term_id").annotate(n=Count("pk")))
    notes = dict(HandoverNote.objects.filter(term_id__in=term_ids).values_list("term_id").annotate(n=Count("pk")))
    suppliers = dict(Supplier.objects.filter(organization_id__in=org_ids).values_list("organization_id").annotate(n=Count("pk")))
    for m, record in zip(chosen, records):
        record["counts"] = {"events": events.get(m.term_id, 0), "suppliers": suppliers.get(m.organization_id, 0),
                            "notes": notes.get(m.term_id, 0)}

    sharers = [m.organization_id for m in chosen if m.role == "EXECUTIVE" and m.term.status == Term.Status.ACTIVE]
    live_codes = share_codes(sharers)
    for record in records:
        if record["id"] in sharers:
            record["can_share_code"] = True
            code = live_codes.get(record["id"])
            if code:
                record["join_code"] = code.code
                record["join_code_expires"] = codes.expires_text(code)
    return records


def attention_for_home(user):
    """Real to-dos across organizations:
    1. Executive sign-offs awaiting this user's approval (PENDING_SIGNOFF).
    2. Handover notes needed from this Executive or Committee Head when Next A.Y. plan is set up.
    3. Join codes the person issued that stop working within two days.
    """
    items = []

    # 1. Pending Executive approvals
    exec_pending_seats = (
        Membership.objects.filter(
            user=user,
            role=Membership.Role.EXECUTIVE,
            term__status=Term.Status.PENDING_SIGNOFF,
        )
        .select_related("organization", "term")
        .order_by("organization__name")
    )
    approved_term_ids = set(
        TermSignOff.objects.filter(
            executive=user, decision=TermSignOff.Decision.APPROVED
        ).values_list("term_id", flat=True)
    )
    seen_approval_terms = set()
    for seat in exec_pending_seats:
        if seat.term_id in approved_term_ids or seat.term_id in seen_approval_terms:
            continue
        seen_approval_terms.add(seat.term_id)
        items.append({
            "id": f"signoff-{seat.term_id}",
            "kind": "approval",
            "title": "Handover is awaiting your approval",
            "org": seat.organization.name,
            "ay": ay_label(seat.term.label),
            "stamp": "Awaiting approval",
            "action": "Approve",
            "url": reverse("signoff_page", args=[seat.organization_id]),
        })

    # 2. Handover notes needed when a TermPlan exists on an ACTIVE term
    officer_active_seats = (
        Membership.objects.filter(
            user=user,
            role__in=[Membership.Role.EXECUTIVE, Membership.Role.COMMITTEE_HEAD],
            term__status=Term.Status.ACTIVE,
        )
        .select_related("organization", "term", "committee")
        .order_by("organization__name")
    )
    planned_term_ids = set(
        TermPlan.objects.filter(
            term_id__in={s.term_id for s in officer_active_seats}
        ).values_list("term_id", flat=True)
    )
    authored_note_term_ids = set(
        HandoverNote.objects.filter(author=user).values_list("term_id", flat=True)
    )
    seen_handover_terms = set()
    for seat in officer_active_seats:
        if (
            seat.term_id not in planned_term_ids
            or seat.term_id in authored_note_term_ids
            or seat.term_id in seen_handover_terms
        ):
            continue
        seen_handover_terms.add(seat.term_id)
        items.append({
            "id": f"handover-{seat.term_id}",
            "kind": "handover",
            "title": "Write your handover note for the next officers",
            "org": seat.organization.name,
            "ay": ay_label(seat.term.label),
            "action": "Write note",
            "url": reverse("handover_list", args=[seat.organization_id]),
        })

    # 3. Expiring join codes within 48 hours
    now = timezone.now()
    soon = now + timedelta(hours=48)
    rows = (JoinCode.objects.filter(created_by=user, revoked_at__isnull=True, expires_at__gt=now, expires_at__lte=soon,
                                    uses_count__lt=F("max_uses"), organization__terms__status=Term.Status.ACTIVE)
            .select_related("organization", "committee").distinct().order_by("expires_at"))
    for row in rows[:20]:
        term = row.organization.terms.filter(status=Term.Status.ACTIVE).first()
        left = timesince(now, row.expires_at).split(",")[0].replace("\xa0", " ")
        items.append({
            "id": row.pk, "kind": "invite", "title": f"Your join code expires in {left}",
            "org": row.organization.name, "ay": ay_label(term.label) if term else "",
            "action": "Manage codes", "url": reverse("joincode_list", args=[row.organization_id]),
        })
    return items[:20]


def activity_for_home(user):
    """Recent seats created in the organizations the person belongs to, newest first. Real, derived from Membership."""
    org_ids = Membership.objects.filter(user=user).values("organization_id")
    rows = (Membership.objects.filter(organization_id__in=org_ids)
            .select_related("user", "organization", "committee", "term").order_by("-created_at", "-pk")[:20])
    feed = []
    for m in rows:
        who = m.user.get_full_name() or m.user.username
        # The founder's seat is created in the same transaction as the organization.
        founded = (m.role == "EXECUTIVE" and m.user_id == m.organization.created_by_id
                   and abs(m.created_at - m.organization.created_at) < timedelta(seconds=10))
        feed.append({
            "id": m.pk, "actor": who,
            "text": "created the organization" if founded else
                    f"joined as {m.get_role_display()}" + (f" in {m.committee.name}" if m.committee else ""),
            "org": m.organization.acronym or m.organization.name, "ay": ay_label(m.term.label), "ago": _ago(m.created_at),
        })
    return feed
