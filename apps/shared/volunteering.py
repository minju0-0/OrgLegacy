"""What happens to a person's event volunteering when their seat ends (leaving, or being removed).

Past events keep them listed: that is history, and their logs stay. Upcoming events drop them, and whoever
planned the event is told, so nobody plans around a volunteer who is no longer in the organization.
"""
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Event, Membership

from .notify import notify


def release_volunteer(user, organization, term):
    """Call after deleting `user`'s seat(s). Does nothing if they still hold another seat in this A.Y."""
    if Membership.objects.filter(user=user, organization=organization, term=term).exists():
        return []
    upcoming = list(Event.objects.filter(organization=organization, term=term, volunteers=user,
                                         date__gte=timezone.localdate()).select_related("created_by"))
    who = user.get_full_name() or user.username
    for event in upcoming:
        event.volunteers.remove(user)
        if event.created_by_id and event.created_by_id != user.pk:
            notify([event.created_by], f"{who} left {organization.name} and is no longer a volunteer for {event.title}.",
                   reverse("event_detail", args=[organization.pk, event.pk]))
    return upcoming
