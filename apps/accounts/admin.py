from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User, Organization, Committee, Term, Membership, JoinCode, Event,
    Supplier, SupplierRating, HandoverNote, TermSignOff, Notification,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_staff"]


admin.site.register([
    Organization, Committee, Term, Membership, JoinCode, Event,
    Supplier, SupplierRating, HandoverNote, TermSignOff, Notification,
])