from datetime import timedelta

from django import forms

from apps.accounts.models import Term
from apps.shared.years import ay_dates, parse_ay


class PlanForm(forms.Form):
    """The next A.Y.: its name (two years in a row) and the dates it runs."""
    academic_year = forms.CharField(
        label="Academic year", max_length=20,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "2027-2028", "autocomplete": "off"}),
        help_text="Two years in a row, like 2027-2028.",
        error_messages={"required": "Enter the academic year, like 2027-2028."})
    start_date = forms.DateField(label="Starts", widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}, format="%Y-%m-%d"),
                                 error_messages={"required": "Enter the day it starts.", "invalid": "Enter a real date."})
    end_date = forms.DateField(label="Ends", widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}, format="%Y-%m-%d"),
                               error_messages={"required": "Enter the day it ends.", "invalid": "Enter a real date."})

    def __init__(self, *args, term, **kwargs):
        super().__init__(*args, **kwargs)
        self.term = term

    @staticmethod
    def suggestion(term, plan=None):
        """What to pre-fill: the saved plan, or the year after this one, June to May."""
        if plan:
            return {"academic_year": plan.label.replace("A.Y. ", ""), "start_date": plan.start_date, "end_date": plan.end_date}
        year = (parse_ay(term.label.replace("A.Y.", "").strip()) or (term.start_date.year, 0))[0] + 1
        start, end = ay_dates(year)
        if start <= term.end_date:
            start = term.end_date + timedelta(days=1)
        return {"academic_year": f"{year}-{year + 1}", "start_date": start, "end_date": end}

    def clean_academic_year(self):
        years = parse_ay(self.cleaned_data["academic_year"])
        if years is None:
            raise forms.ValidationError("Enter two years in a row, like 2027-2028.")
        label = f"A.Y. {years[0]}-{years[1]}"
        if Term.objects.filter(organization=self.term.organization, label__iexact=label).exists():
            raise forms.ValidationError(f"{label} already exists for this organization.")
        self.label = label
        return self.cleaned_data["academic_year"]

    def clean(self):
        data = super().clean()
        start, end = data.get("start_date"), data.get("end_date")
        if start and start <= self.term.end_date:
            self.add_error("start_date", f"It must start after the current A.Y. ends on {self.term.end_date:%-d %b %Y}.")
        if start and end:
            if end <= start:
                self.add_error("end_date", "It must end after it starts.")
            elif (end - start).days > 550:
                self.add_error("end_date", "An A.Y. should not run longer than 18 months. Check the dates.")
        return data
