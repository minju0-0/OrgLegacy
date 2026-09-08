from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Extends Django's built-in User with the role-based fields OrgLegacy
    needs: every account belongs to a student organization and holds
    one of three roles (Officer, Member, Adviser), matching the
    role-based dashboards described in the proposal.
    """

    ROLE_OFFICER = 'officer'
    ROLE_MEMBER = 'member'
    ROLE_ADVISER = 'adviser'

    ROLE_CHOICES = [
        (ROLE_OFFICER, 'Student Officer'),
        (ROLE_MEMBER, 'General Member'),
        (ROLE_ADVISER, 'Faculty Adviser'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    organization_name = models.CharField(max_length=150, blank=True, default='', help_text="e.g. Computer Science Society")
    student_status = models.CharField(max_length=100, blank=True, default='', help_text="e.g. 3rd Year, Alumni")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
