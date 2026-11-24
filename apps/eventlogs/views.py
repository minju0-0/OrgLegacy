"""Event logs: a volunteer's own account of an event, inside the event.

Only people picked as volunteers on the event may write logs, and only once the event's day has come (a log is
what happened, so it cannot be written before it did). A volunteer may write several, and edits or deletes only their
own. An Executive may delete any log (to remove something that does not belong) but never edits another person's words.
The event page (apps/events) draws the logs and the dialogs; this slice takes the submissions.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.accounts.models import Event, EventLog
from apps.shared.permissions import OrgRoleRequiredMixin

TEXT_MAX = 5000


class LogBase(OrgRoleRequiredMixin, View):
    require_open_term = True

    def event(self):
        return get_object_or_404(Event, pk=self.kwargs["pk"], organization=self.access.organization, term=self.access.term)

    def back(self, event):
        return redirect(reverse("event_detail", args=[self.access.organization.pk, event.pk]))

    def text(self, request, event):
        """(what_happened, lessons) from the form, or None after telling the person what is wrong."""
        what = (request.POST.get("what_happened") or "").strip()
        lessons = (request.POST.get("challenges_lessons") or "").strip()
        if not what:
            messages.error(request, "Say what happened. Your log was not saved.")
        elif len(what) > TEXT_MAX or len(lessons) > TEXT_MAX:
            messages.error(request, f"Keep each part under {TEXT_MAX} characters. Your log was not saved.")
        else:
            return what, lessons
        return None


class LogAdd(LogBase):
    def post(self, request, org_id, pk):
        event = self.event()
        if not event.volunteers.filter(pk=request.user.pk).exists():
            messages.error(request, "Only the volunteers picked for this event can write logs on it.")
            return self.back(event)
        if event.date > timezone.localdate():
            messages.info(request, f"Logs open on {event.date:%-d %b %Y}, the day of the event.")
            return self.back(event)
        text = self.text(request, event)
        if text:
            EventLog.objects.create(event=event, author=request.user, what_happened=text[0], challenges_lessons=text[1])
            messages.success(request, "Your log was added.")
        return self.back(event)


class LogEdit(LogBase):
    def post(self, request, org_id, pk, log_pk):
        event = self.event()
        log = get_object_or_404(EventLog, pk=log_pk, event=event)
        if log.author_id != request.user.pk:
            messages.error(request, "You can only edit your own logs.")
            return self.back(event)
        text = self.text(request, event)
        if text:
            log.what_happened, log.challenges_lessons = text
            log.save()
            messages.success(request, "Your log was updated.")
        return self.back(event)


class LogDelete(LogBase):
    def post(self, request, org_id, pk, log_pk):
        event = self.event()
        log = get_object_or_404(EventLog, pk=log_pk, event=event)
        if not (log.author_id == request.user.pk or self.access.is_executive):
            messages.error(request, "You can only delete your own logs.")
            return self.back(event)
        log.delete()
        messages.success(request, "The log was deleted.")
        return self.back(event)
