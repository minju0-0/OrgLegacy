"""Notifications: mark them read, and follow one to where it points. Writing them is apps/shared/notify.py."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.models import Notification
from apps.shared.http import json_login_required


@require_POST
@json_login_required
def read_all_view(request):
    """Bell hook notifications:mark-all-read."""
    changed = Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return JsonResponse({"marked": changed})


@login_required
def go_view(request, pk):
    """Mark one notification read, then forward to its link (a path on this site) or Home."""
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not note.read:
        note.read = True
        note.save(update_fields=["read"])
    target = note.link or "/home/"
    if not url_has_allowed_host_and_scheme(target, allowed_hosts=None) or target.startswith("//"):
        target = "/home/"
    return redirect(target)
