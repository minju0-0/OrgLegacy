"""Design preview data for Profile. DEBUG only.

Open /profile/?preview=full  (every future section filled)  |  empty  (no seats)  |  bare  (what you have today).

DELETE THIS FILE, and the lines in views.py that use it, once the real data is wired.
"""
from django import forms

from .forms import UserDetailsForm


class PreviewDetailsForm(UserDetailsForm):
    """Shows how extra profile fields look once the model has them. Remove with the preview."""
    course = forms.CharField(label="Course", required=False, max_length=80, initial="BS Computer Science",
                             widget=forms.TextInput(attrs={"placeholder": "Your course"}))
    year_level = forms.ChoiceField(label="Year level", required=False, initial="3",
                                   choices=[("", "Select"), ("1", "1st year"), ("2", "2nd year"), ("3", "3rd year"), ("4", "4th year"), ("5", "5th year or higher")])
    phone = forms.CharField(label="Contact number", required=False, max_length=20, initial="0917 555 0142",
                            widget=forms.TextInput(attrs={"placeholder": "Optional", "inputmode": "tel", "autocomplete": "tel"}))
    bio = forms.CharField(label="About you", required=False, max_length=280,
                          initial="Treasurer at JPCS. I keep the books and the supplier list in order.",
                          help_text="A line or two other officers see. Up to 280 characters.",
                          widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("course", "year_level", "phone", "bio"):
            self.fields[name].widget.attrs["class"] = "form-input"


def _seat(i, name, acr, role, code, ay, status, title="", committee=""):
    return {"id": i, "name": name, "acronym": acr, "role": role, "role_code": code, "ay": ay, "status": status,
            "title": title, "committee": committee}


SEATS = [
    _seat(1, "Junior Philippine Computer Society", "JPCS", "Executive", "EXECUTIVE", "A.Y. 2026-2027", "ACTIVE", title="Treasurer"),
    _seat(2, "CIT Debate Society", "CDS", "Committee Head", "COMMITTEE_HEAD", "A.Y. 2026-2027", "PENDING_SIGNOFF", committee="Logistics"),
    _seat(3, "Rotaract Club of Cebu Tech", "RCCT", "Executive", "EXECUTIVE", "A.Y. 2025-2026", "PENDING_SIGNOFF", title="President"),
    _seat(1, "Junior Philippine Computer Society", "JPCS", "Member", "MEMBER", "A.Y. 2025-2026", "CLOSED", committee="Events"),
    _seat(5, "Culture and Arts Guild", "CAG", "Member", "MEMBER", "A.Y. 2025-2026", "CLOSED", committee="Production"),
    _seat(6, "Mathematics Society", "MATHSOC", "Committee Head", "COMMITTEE_HEAD", "A.Y. 2025-2026", "CLOSED", committee="Academics"),
    _seat(3, "Rotaract Club of Cebu Tech", "RCCT", "Committee Head", "COMMITTEE_HEAD", "A.Y. 2024-2025", "CLOSED", committee="Finance"),
    _seat(1, "Junior Philippine Computer Society", "JPCS", "Member", "MEMBER", "A.Y. 2024-2025", "CLOSED", committee="Events"),
]

STATS = [
    {"label": "Events added", "value": 14},
    {"label": "Suppliers rated", "value": 6},
    {"label": "Handover notes written", "value": 3},
]


def preview_context(name):
    """Returns context overrides plus 'use_preview_form' so the view swaps in PreviewDetailsForm."""
    if name == "bare":
        return {"preview": "bare"}
    if name == "empty":
        return {"preview": "empty", "organizations": [], "use_preview_form": True}
    return {"preview": "full", "organizations": SEATS, "profile_stats": STATS, "use_preview_form": True}
