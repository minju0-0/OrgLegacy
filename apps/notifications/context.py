"""The bell in the top bar, on every app page. Supplies `notifications`, `notifications_unread`, and `notifications_has_more`.

Each row is {id, text, org, ago, unread, url}. `url` goes through notifications:go, which marks
the row read and then forwards to the notification's own link.
"""
from django.urls import reverse

from apps.accounts.models import Notification
from apps.shared.selectors import _ago

SHOWN = 8


def format_notification(n):
    return {
        "id": n.pk,
        "text": n.message,
        "org": "",
        "ago": _ago(n.created_at),
        "unread": not n.read,
        "url": reverse("notifications_go", args=[n.pk]),
    }


def bell(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    qs = Notification.objects.filter(recipient=user).order_by("-created_at", "-pk")
    rows = list(qs[:SHOWN + 1])
    has_more = len(rows) > SHOWN
    rows = rows[:SHOWN]
    return {
        "notifications": [format_notification(n) for n in rows],
        "notifications_unread": Notification.objects.filter(recipient=user, read=False).count(),
        "notifications_has_more": has_more,
    }
