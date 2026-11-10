"""Join code rules, kept in one place so the issuing slice (joincodes), the redeeming slice (join)
and the Home selectors all agree on what a code is and when it can be used.

A code never stores a term. At redemption the organization's ACTIVE term is looked up (docs plan, section 2).
"""
import re
import secrets
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import JoinCode, Term

# No 0/O or 1/I: a code is read aloud and typed from a phone screen.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8

# How long a code may live. Head codes stay in hours, not days (plan, section 2).
MEMBER_EXPIRY_HOURS = (24, 72, 168, 336)
HEAD_EXPIRY_HOURS = (1, 6, 24)
MEMBER_USES = (1, 5, 10, 25, 50, 100)
QUICK_HOURS = 168          # the Home "share a code" button: seven days
QUICK_USES = 25


def new_code_value():
    """A fresh 8-character code that does not exist yet."""
    for _ in range(20):
        value = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if not JoinCode.objects.filter(code=value).exists():
            return value
    raise RuntimeError("Could not find an unused join code.")


def normalize(raw):
    """Typed or pasted text -> 8 characters, or '' if it cannot be a code. Accepts 'OL-4F7K-92QD'."""
    text = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
    if len(text) > CODE_LENGTH and text.startswith("OL"):
        text = text[2:]
    return text if len(text) == CODE_LENGTH else ""


def pretty(value):
    return f"OL-{value[:4]}-{value[4:]}"


def expires_text(code):
    return "Expires " + timezone.localtime(code.expires_at).strftime("%-d %b, %-I:%M %p")


def is_valid_now(code, now=None):
    return state(code, now) == "active"


def state(code, now=None):
    """'active' | 'revoked' | 'expired' | 'used'. The one word shown beside a code."""
    now = now or timezone.now()
    if code.revoked_at:
        return "revoked"
    if code.expires_at <= now:
        return "expired"
    if code.uses_count >= code.max_uses:
        return "used"
    return "active"


STATE_LABEL = {"active": "Active", "revoked": "Revoked", "expired": "Expired", "used": "Used up"}


def redeem_problem(code, term, now=None):
    """Why a code cannot be redeemed right now, as a sentence for the person, or None when it can.

    `term` is the organization's ACTIVE term (or None). Call this inside the transaction that locks the row.
    """
    now = now or timezone.now()
    s = state(code, now)
    if s == "revoked":
        return "That code was cancelled. Ask an officer for a new one."
    if s == "expired":
        return "That code has expired. Ask an officer for a new one."
    if s == "used":
        return "That code has already been used up. Ask an officer for a new one."
    if term is None or term.status != Term.Status.ACTIVE:
        return "This organization is not taking new members right now."
    if code.committee_id and not code.committee.is_active:
        return "That committee is no longer active. Ask an officer for a new code."
    return None


def expiry_from_hours(hours):
    return timezone.now() + timedelta(hours=hours)
