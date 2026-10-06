"""Read-side queries shared by the Home and Profile slices.

Both pages describe the same thing: the places a user holds a seat. A seat is a
Membership (user + organization + term + role). Each record returned here is a
plain dict so templates stay free of ORM details.
"""
import re

from django.db.models import Count, OuterRef, Subquery

from apps.accounts.models import Membership, Term

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
            "id": m.pk,
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
            "url": None,        # no organization page exists yet; the template hides the button
        })
    return out


def _base(user):
    return (Membership.objects.filter(user=user)
            .select_related("organization", "committee", "term"))


def memberships_for_profile(user):
    """Every seat the user has held, newest A.Y. first. Powers the Profile ledger."""
    return _records(_base(user).order_by("-term__start_date", "organization__name", "pk"))


def organizations_for_home(user):
    """One card per organization: the user's live seat if they have one, else their latest.

    A person can hold two seats in one A.Y. (a committee seat and an executive seat);
    the highest role wins the card. Live organizations sort before closed ones.
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
    return _records(chosen)
