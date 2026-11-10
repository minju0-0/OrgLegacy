from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Committee, Event, Membership

User = get_user_model()


class VolunteerField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, user):
        return f"{user.get_full_name() or user.username} (@{user.username})"


class EventForm(forms.ModelForm):
    """Plan an event. Volunteers are picked from the organization's members, never typed.

    Executives choose the committee tag and the budget. A Committee Head's events are always their own committee's
    and carry no budget field, so a head can never overwrite what the Executives set.
    """
    volunteers = VolunteerField(queryset=User.objects.none(), required=False, label="Volunteers",
                                widget=forms.CheckboxSelectMultiple,
                                help_text="Only people picked here can write logs on this event.")

    class Meta:
        model = Event
        fields = ["title", "date", "committee", "budget", "description", "volunteers"]
        labels = {"title": "Event name", "date": "Date", "committee": "Committee", "budget": "Budget (PHP)",
                  "description": "What is it for"}
        help_texts = {"committee": "Leave as the whole organization, or tie it to one committee.",
                      "date": "Plan ahead or record one that already happened. Logs open on this day."}
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "autocomplete": "off", "placeholder": "Freshmen Orientation"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}, format="%Y-%m-%d"),
            "committee": forms.Select(attrs={"class": "form-input"}),
            "budget": forms.NumberInput(attrs={"class": "form-input", "min": "0", "step": "0.01", "inputmode": "decimal"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
        }
        error_messages = {"title": {"required": "Give the event a name."}, "date": {"required": "Enter the date it happens."},
                          "description": {"required": "Say what the event is for, even in a sentence."}}

    def __init__(self, *args, access, **kwargs):
        super().__init__(*args, **kwargs)
        self.access = access
        seats = Membership.objects.filter(organization=access.organization, term=access.term).values("user")
        self.fields["volunteers"].queryset = User.objects.filter(pk__in=seats).order_by("first_name", "last_name", "username")
        if access.is_executive:
            current = self.instance.committee_id
            self.fields["committee"].queryset = Committee.objects.filter(
                Q(organization=access.organization, is_active=True) | Q(pk=current)).order_by("name")
            self.fields["committee"].empty_label = "Whole organization"
            self.fields["committee"].required = False
        else:
            del self.fields["committee"]
            del self.fields["budget"]

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        if not title:
            raise forms.ValidationError("Give the event a name.")
        return title

    def clean_date(self):
        date, term = self.cleaned_data["date"], self.access.term
        if not term.start_date <= date <= term.end_date:
            raise forms.ValidationError(
                f"This A.Y. runs {term.start_date:%-d %b %Y} to {term.end_date:%-d %b %Y}. Pick a date inside it.")
        if self.instance.pk and date > timezone.localdate() and self.instance.logs.exists():
            raise forms.ValidationError("Volunteers have already written logs, so this event cannot move to a later date.")
        return date

    def clean_budget(self):
        budget = self.cleaned_data["budget"]
        if budget is not None and budget < 0:
            raise forms.ValidationError("A budget cannot be negative.")
        return budget if budget is not None else 0

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if not text:
            raise forms.ValidationError("Say what the event is for, even in a sentence.")
        return text

    def clean(self):
        data = super().clean()
        if not self.access.is_executive:
            committee = self.access.committee
            if committee is None or not committee.is_active:
                raise forms.ValidationError("Your committee is not active, so you cannot plan events for it.")
        return data
