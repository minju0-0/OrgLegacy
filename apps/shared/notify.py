"""Write a bell notification. Any slice can call this; only the notifications slice reads them back."""
from apps.accounts.models import Notification


def notify(recipients, message, link=""):
    """One Notification per recipient. `link` is a relative path such as /organizations/3/members/."""
    rows = [Notification(recipient=r, message=message[:255], link=link[:255]) for r in recipients]
    if rows:
        Notification.objects.bulk_create(rows)
