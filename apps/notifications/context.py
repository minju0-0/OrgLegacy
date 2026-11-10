"""The bell in the top bar, on every app page. Supplies `notifications` and `notifications_unread`.

Each row is {id, text, org, ago, unread, url}. `url` goes through notifications:go, which marks
the row read and then forwards to the notification's own link.
"""
from django.urls import reverse

from apps.accounts.models import Notification
from apps.shared.selectors import _ago

SHOWN = 8


def bell(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    rows = list(Notification.objects.filter(recipient=user).order_by("-created_at", "-pk")[:SHOWN])
    return {
        "notifications": [{"id": n.pk, "text": n.message, "org": "", "ago": _ago(n.created_at),
                           "unread": not n.read, "url": reverse("notifications_go", args=[n.pk])} for n in rows],
        "notifications_unread": Notification.objects.filter(recipient=user, read=False).count(),
    }
