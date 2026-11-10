"""Events: plan what the organization does, so the next officers can learn from it.

An event is planned first (by an Executive or a Committee Head), with volunteers picked from the members.
What happened, and what was learned, is written afterwards by those volunteers as logs (apps/eventlogs).
This slice owns planning, reading, correcting and deleting events. Home and the organization page only read a
summary (apps/shared/selectors.py). Everything is scoped to the A.Y. the person works in (docs plan, Phase 3).

  read     any member (an alumnus reads the A.Y. they served in)
  plan     Executives (any committee or the whole organization) and Committee Heads (their own committee)
  correct  Executives; a Committee Head only for their own committee's events
  delete   Executives only, and only the Executives set the budget
Dates may be future or past. Logging is what waits for the day (see eventlogs).
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Event
from apps.shared.notify import notify
from apps.shared.permissions import EXECUTIVE, HEAD, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import EventForm

PLANNERS = (EXECUTIVE, HEAD)


def term_events(access):
    return Event.objects.filter(organization=access.organization, term=access.term).select_related("committee", "created_by")


def can_correct(access, event):
    """Executives correct anything; a Committee Head only their own committee's events."""
    if not access.is_open:
        return False
    return access.is_executive or (access.is_head and access.committee_id is not None and event.committee_id == access.committee_id)


def base_context(access, **extra):
    context = {"access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
               "org_nav": org_nav(access), "active_page": "event_list",
               "can_plan": access.is_open and access.role in PLANNERS}
    context.update(extra)
    return context


def list_context(access):
    """The log: upcoming first (soonest first), then past (latest first)."""
    today = timezone.localdate()
    events = list(term_events(access).annotate(volunteer_count=Count("volunteers", distinct=True),
                                               log_count=Count("logs", distinct=True)).order_by("date", "pk"))
    upcoming = [e for e in events if e.date >= today]
    past = [e for e in reversed(events) if e.date < today]
    return {"rows": [{"event": e, "upcoming": True} for e in upcoming] + [{"event": e, "upcoming": False} for e in past],
            "total": len(events)}


def tell_new_volunteers(event, access, actor, before):
    """Volunteers added by this save, other than the person who saved it, are told they were picked."""
    added = [u for u in event.volunteers.all() if u.pk not in before and u.pk != actor.pk]
    notify(added, f"You were added as a volunteer for {event.title}.",
           reverse("event_detail", args=[access.organization.pk, event.pk]))


class EventList(OrgRoleRequiredMixin, TemplateView):
    template_name = "events/events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(base_context(self.access), **list_context(self.access))
        if context["can_plan"]:
            context["form"] = EventForm(access=self.access)
        return context


class EventDetail(OrgRoleRequiredMixin, View):
    def get(self, request, org_id, pk):
        access = self.access
        event = get_object_or_404(term_events(access), pk=pk)
        today = timezone.localdate()
        volunteers = list(event.volunteers.order_by("first_name", "last_name", "username"))
        is_volunteer = any(v.pk == request.user.pk for v in volunteers)
        logs = [{"log": log,
                 "can_edit": access.is_open and log.author_id == request.user.pk,
                 "can_delete": access.is_open and (log.author_id == request.user.pk or access.is_executive)}
                for log in event.logs.select_related("author")]
        context = base_context(
            access, event=event, volunteers=volunteers, logs=logs, today=today,
            can_edit=can_correct(access, event), can_delete=access.is_open and access.is_executive,
            is_volunteer=is_volunteer, logging_open=event.date <= today,
            can_log=access.is_open and is_volunteer and event.date <= today,
            wait_to_log=access.is_open and is_volunteer and event.date > today,
            ay=ay_label(access.term.label))
        return render(request, "events/event_detail.html", context)


class EventCreate(OrgRoleRequiredMixin, View):
    """Plan an event. The form is a dialog on the Events page, so a mistake sends that page back with the dialog open."""
    allowed_roles = PLANNERS
    require_open_term = True

    def get(self, request, org_id):
        return redirect(reverse("event_list", args=[self.access.organization.pk]))

    def post(self, request, org_id):
        access = self.access
        form = EventForm(request.POST, access=access)
        if not form.is_valid():
            context = base_context(access, form=form, open_dialog="event-add-modal", **list_context(access))
            return render(request, "events/events.html", context, status=400)
        event = form.save(commit=False)
        event.organization, event.term, event.created_by = access.organization, access.term, request.user
        if not access.is_executive:
            event.committee = access.committee
        event.save()
        form.save_m2m()
        tell_new_volunteers(event, access, request.user, before=set())
        messages.success(request, f"{event.title} is planned for {event.date:%-d %b %Y}.")
        return redirect(reverse("event_detail", args=[access.organization.pk, event.pk]))


class EventEdit(OrgRoleRequiredMixin, View):
    """Correct an event or change who volunteers. Longer than a dialog should hold, so this one is a page."""
    allowed_roles = PLANNERS
    require_open_term = True

    def get_event(self):
        event = get_object_or_404(term_events(self.access), pk=self.kwargs["pk"])
        if not can_correct(self.access, event):
            raise PermissionDenied("Committee Heads can only change their own committee's events.")
        return event

    def page(self, request, event, form, status=200):
        return render(request, "events/event_form.html", base_context(self.access, form=form, event=event), status=status)

    def get(self, request, org_id, pk):
        event = self.get_event()
        return self.page(request, event, EventForm(instance=event, access=self.access))

    def post(self, request, org_id, pk):
        event = self.get_event()
        before = set(event.volunteers.values_list("pk", flat=True))
        form = EventForm(request.POST, instance=event, access=self.access)
        if not form.is_valid():
            return self.page(request, get_object_or_404(term_events(self.access), pk=pk), form, status=400)
        form.save()
        tell_new_volunteers(event, self.access, request.user, before)
        messages.success(request, f"{event.title} was updated.")
        return redirect(reverse("event_detail", args=[self.access.organization.pk, event.pk]))


class EventDelete(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id, pk):
        event = get_object_or_404(term_events(self.access), pk=pk)
        title, count = event.title, event.logs.count()
        event.delete()
        extra = f" Its {count} log{'s' if count != 1 else ''} went with it." if count else ""
        messages.success(request, f"{title} was deleted.{extra}")
        return redirect(reverse("event_list", args=[self.access.organization.pk]))
