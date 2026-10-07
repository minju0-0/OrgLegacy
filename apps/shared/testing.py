"""Factories for the slices' tests. Not imported by anything at runtime."""
from datetime import date, timedelta
from itertools import count

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Committee, JoinCode, Membership, Organization, Term

_n = count(1)
User = get_user_model()


def make_user(name=None, **extra):
    name = name or f"user{next(_n)}"
    return User.objects.create_user(username=name, password="pass-12345", first_name=name.title(), last_name="Test",
                                    email=f"{name}@example.edu.ph", **extra)


def make_org(owner=None, name="Test Society", status=Term.Status.ACTIVE, label="A.Y. 2026-2027"):
    owner = owner or make_user()
    org = Organization.objects.create(name=name, acronym="TS", created_by=owner)
    term = Term.objects.create(organization=org, label=label, start_date=date(2026, 6, 1), end_date=date(2027, 5, 31), status=status)
    Membership.objects.create(user=owner, organization=org, term=term, role=Membership.Role.EXECUTIVE)
    return org, term, owner


def add_seat(user, org, term, role=Membership.Role.MEMBER, committee=None):
    return Membership.objects.create(user=user, organization=org, term=term, role=role, committee=committee)


def make_committee(org, name="Logistics", active=True):
    return Committee.objects.create(organization=org, name=name, is_active=active)


def make_code(org, creator, value="ABCD2345", role=JoinCode.Role.MEMBER, committee=None, max_uses=1, hours=24, **extra):
    return JoinCode.objects.create(code=value, organization=org, committee=committee, role=role, max_uses=max_uses,
                                   created_by=creator, expires_at=timezone.now() + timedelta(hours=hours), **extra)
