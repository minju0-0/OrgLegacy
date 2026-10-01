from django.conf import settings
from django.http import Http404
from django.shortcuts import render


def landing_view(request):
    return render(request, "landing/landing.html")


def styleguide_view(request):
    """Dev-only component gallery. 404s unless DEBUG is on."""
    if not settings.DEBUG:
        raise Http404
    return render(request, "styleguide.html", {"active_page": "styleguide"})