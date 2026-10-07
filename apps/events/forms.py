from django import forms

from apps.accounts.models import Event


class EventForm(forms.ModelForm):
    """Log or correct one event. The budget is the Executives' to set (plan, section 3), so only they are offered it."""

    class Meta:
        model = Event
        fields = ["title", "date", "budget", "description", "volunteers", "challenges_lessons"]
        labels = {"title": "Event name", "date": "Date", "budget": "Budget (PHP)", "description": "What happened",
                  "volunteers": "Volunteers", "challenges_lessons": "Challenges and lessons"}
        help_texts = {
            "volunteers": "Who helped, and with what. One per line works well.",
            "challenges_lessons": "What went wrong, what you would change. This is what next year's officers read first.",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "autocomplete": "off", "placeholder": "Freshmen Orientation"}),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}, format="%Y-%m-%d"),
            "budget": forms.NumberInput(attrs={"class": "form-input", "min": "0", "step": "0.01", "inputmode": "decimal"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "volunteers": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "challenges_lessons": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
        }
        error_messages = {"title": {"required": "Give the event a name."}, "date": {"required": "Enter the date it happened or will happen."},
                          "description": {"required": "Say what the event was, even in a sentence."}}

    def __init__(self, *args, access, **kwargs):
        super().__init__(*args, **kwargs)
        self.access = access
        if not access.is_executive:
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
        return date

    def clean_budget(self):
        budget = self.cleaned_data["budget"]
        if budget is not None and budget < 0:
            raise forms.ValidationError("A budget cannot be negative.")
        return budget if budget is not None else 0

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if not text:
            raise forms.ValidationError("Say what the event was, even in a sentence.")
        return text
