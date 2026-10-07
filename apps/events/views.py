"""Events: log what the organization did, so the next officers can learn from it.

This slice owns creating, reading, correcting and deleting events. Home and the organization page only
read a summary of them (apps/shared/selectors.py). Everything is scoped to the A.Y. the person works in
(docs plan, Phase 3), so an event always belongs to the organization's ACTIVE term and cannot be edited later.

  read    any member            (an alumnus reads the A.Y. they served in)
  log     any member            Members contribute to the event log
  correct Committee Heads and Executives
  delete  Executives only        and only the Executives set the budget
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Event
from apps.shared.permissions import EXECUTIVE, HEAD, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import EventForm


def term_events(access):
    return Event.objects.filter(organization=access.organization, term=access.term)


def base_context(access, **extra):
    context = {"access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
               "org_nav": org_nav(access), "active_page": "event_list"}
    context.update(extra)
    return context


class EventList(OrgRoleRequiredMixin, TemplateView):
    template_name = "events/events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        events = list(term_events(self.access).order_by("date", "pk"))
        upcoming = [e for e in events if e.date >= today]
        past = [e for e in reversed(events) if e.date < today]
        context.update(rows=[{"event": e, "upcoming": True} for e in upcoming] + [{"event": e, "upcoming": False} for e in past],
                       ay=ay_label(self.access.term.label), active_page="event_list", can_log=self.access.is_open,
                       total=len(events))
        return context


class EventDetail(OrgRoleRequiredMixin, TemplateView):
    template_name = "events/event_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        context.update(event=get_object_or_404(term_events(access), pk=self.kwargs["pk"]), ay=ay_label(access.term.label),
                       active_page="event_list", can_edit=access.is_open and access.role in (EXECUTIVE, HEAD),
                       can_delete=access.is_open and access.is_executive, today=timezone.localdate())
        return context


class EventFormPage(OrgRoleRequiredMixin, View):
    """Shared by log and correct: one form page, saved to the person's own A.Y."""
    require_open_term = True
    event = None
    heading = ""

    def get_event(self):
        return None

    def page(self, request, form, status=200):
        return render(request, "events/event_form.html", base_context(
            self.access, form=form, event=self.event, heading=self.heading, ay=ay_label(self.access.term.label)), status=status)

    def get(self, request, org_id, **kw):
        self.event = self.get_event()
        return self.page(request, self.form_class(instance=self.event, access=self.access))

    def post(self, request, org_id, **kw):
        self.event = self.get_event()
        form = self.form_class(request.POST, instance=self.event, access=self.access)
        if not form.is_valid():
            return self.page(request, form, status=400)
        event = form.save(commit=False)
        event.organization, event.term = self.access.organization, self.access.term
        event.save()
        messages.success(request, self.done.format(title=event.title))
        return redirect(reverse("event_detail", args=[self.access.organization.pk, event.pk]))


class EventCreate(EventFormPage):
    form_class = EventForm
    heading = "Log an event"
    done = "{title} is in the log."


class EventEdit(EventFormPage):
    allowed_roles = (EXECUTIVE, HEAD)
    form_class = EventForm
    heading = "Edit event"
    done = "{title} was updated."

    def get_event(self):
        return get_object_or_404(term_events(self.access), pk=self.kwargs["pk"])


class EventDelete(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id, pk):
        event = get_object_or_404(term_events(self.access), pk=pk)
        title = event.title
        event.delete()
        messages.success(request, f"{title} was deleted from the log.")
        return redirect(reverse("event_list", args=[self.access.organization.pk]))
