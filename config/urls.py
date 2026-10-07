"""
URL configuration for config project.

The urlpatterns list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.landing.urls")),
    path("login/", include("apps.login.urls")),
    path("register/", include("apps.register.urls")),
    path("home/", include("apps.home.urls")),
    path("profile/", include("apps.profile.urls")),
    path("settings/", include("apps.settings.urls")),

    # Organization and membership slices. The first four share the /organizations/ prefix;
    # each owns its own patterns and names (see each app's urls.py).
    path("organizations/", include("apps.organizations.urls")),
    path("organizations/", include("apps.committees.urls")),
    path("organizations/", include("apps.members.urls")),
    path("organizations/", include("apps.joincodes.urls")),
    path("organizations/", include("apps.events.urls")),
    path("join/", include("apps.join.urls")),
    path("notifications/", include("apps.notifications.urls")),
]