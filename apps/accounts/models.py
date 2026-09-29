"""
Tables: User, Organization, Committee, Term, Membership, JoinCode,
Event, Supplier, SupplierRating, HandoverNote, TermSignOff, Notification
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# User
class User(AbstractUser):


    def __str__(self):
        return self.username


# Organization
class Organization(models.Model):
    name = models.CharField(max_length=150)
    acronym = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# Committee
class Committee(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="committees"
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)  # soft-delete keeps history

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self):
        return f"{self.name} ({self.organization})"


# Term
class Term(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PENDING_SIGNOFF = "PENDING_SIGNOFF", "Pending Sign-off"
        CLOSED = "CLOSED", "Closed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="terms"
    )
    label = models.CharField(max_length=100)  # e.g. "A.Y. 2026-2027"
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        constraints = [
            # Only one live (ACTIVE / PENDING_SIGNOFF) term per organization
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(status__in=["ACTIVE", "PENDING_SIGNOFF"]),
                name="one_live_term_per_organization",
            ),
        ]

    def __str__(self):
        return f"{self.organization} - {self.label}"


# Membership  (junction: User <-> Organization / Committee / Term)
class Membership(models.Model):
    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Member"
        COMMITTEE_HEAD = "COMMITTEE_HEAD", "Committee Head"
        EXECUTIVE = "EXECUTIVE", "Executive"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="memberships"
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER
    )
    title = models.CharField(max_length=100, blank=True)  # e.g. "Treasurer"
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    appointment_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # One executive/head seat per user per org per term
            models.UniqueConstraint(
                fields=["user", "organization", "term"],
                condition=models.Q(role__in=["EXECUTIVE", "COMMITTEE_HEAD"]),
                name="one_leadership_seat_per_org_per_term",
            ),
            # No double-joining the same committee within a term
            models.UniqueConstraint(
                fields=["user", "organization", "committee", "term"],
                condition=models.Q(role="MEMBER"),
                name="one_committee_seat_per_org_per_term",
            ),
            # A committee cannot have two heads in the same term
            models.UniqueConstraint(
                fields=["organization", "committee", "term"],
                condition=models.Q(role="COMMITTEE_HEAD"),
                name="one_head_per_committee_per_term",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.role} ({self.term})"


# JoinCode
class JoinCode(models.Model):
    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Member"
        COMMITTEE_HEAD = "COMMITTEE_HEAD", "Committee Head"

    code = models.CharField(max_length=12, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="join_codes"
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="join_codes",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    max_uses = models.PositiveIntegerField(default=1)
    uses_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_codes",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code


# Event
class Event(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events"
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=200)
    date = models.DateField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField()
    volunteers = models.TextField(blank=True)
    challenges_lessons = models.TextField(blank=True)

    def __str__(self):
        return self.title


# Supplier
class Supplier(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="suppliers"
    )
    name = models.CharField(max_length=150)
    contact_info = models.TextField()
    cost_notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


# SupplierRating
class SupplierRating(models.Model):
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="ratings"
    )
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supplier_ratings",
    )
    score = models.PositiveSmallIntegerField()  # 1 to 5
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.supplier} - {self.score}/5"


# HandoverNote
class HandoverNote(models.Model):
    class Scope(models.TextChoices):
        COMMITTEE = "COMMITTEE", "Committee"
        ORGANIZATION = "ORGANIZATION", "Organization"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="handover_notes"
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name="handover_notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="handover_notes",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    committee = models.ForeignKey(
        Committee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handover_notes",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scope} note - {self.term}"


# TermSignOff
class TermSignOff(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes Requested"

    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name="sign_offs"
    )
    executive = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="term_sign_offs",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("term", "executive")

    def __str__(self):
        return f"{self.executive} - {self.decision}"


# Notification
class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message