from django import forms

from apps.accounts.models import Committee, JoinCode, Membership
from apps.shared import codes

HOUR_LABELS = {1: "1 hour", 6: "6 hours", 24: "24 hours", 72: "3 days", 168: "7 days", 336: "14 days"}
ALL_HOURS = sorted(set(codes.MEMBER_EXPIRY_HOURS) | set(codes.HEAD_EXPIRY_HOURS))


class JoinCodeForm(forms.Form):
    """Make a join code. What a person may ask for depends on their seat (docs plan, section 2):

    Executive        a Member code (one committee or all) or a Committee Head code for one committee.
    Committee Head   a Member code, locked to their own committee.
    A Head code is single use (a committee has one head per A.Y.) and lives hours, not days.
    """
    role = forms.ChoiceField(label="Who is it for", widget=forms.Select(attrs={"class": "form-input"}))
    committee = forms.ModelChoiceField(label="Committee", queryset=Committee.objects.none(), required=False,
                                       empty_label="All committees", widget=forms.Select(attrs={"class": "form-input"}))
    max_uses = forms.TypedChoiceField(label="How many people", coerce=int, choices=[(n, str(n)) for n in codes.MEMBER_USES],
                                      initial=codes.QUICK_USES, widget=forms.Select(attrs={"class": "form-input"}))
    hours = forms.TypedChoiceField(label="Works for", coerce=int, choices=[(h, HOUR_LABELS[h]) for h in ALL_HOURS],
                                   initial=codes.QUICK_HOURS, widget=forms.Select(attrs={"class": "form-input"}))

    def __init__(self, *args, access, **kwargs):
        super().__init__(*args, **kwargs)
        self.access = access
        member, head = JoinCode.Role.MEMBER, JoinCode.Role.COMMITTEE_HEAD
        active = Committee.objects.filter(organization=access.organization, is_active=True).order_by("name")
        if access.is_executive:
            self.fields["role"].choices = [(member, "A Member"), (head, "A Committee Head")]
            self.fields["committee"].queryset = active
        else:   # a Committee Head: Members of their own committee only, so the committee field is not offered
            self.fields["role"].choices = [(member, "A Member of " + (access.committee.name if access.committee else "your committee"))]
            self.fields["committee"].queryset = active.filter(pk=access.committee_id)
            self.fields["committee"].widget = forms.HiddenInput()
        self.fields["role"].initial = member

    def clean(self):
        data = super().clean()
        role, committee = data.get("role"), data.get("committee")
        if not role or self.errors.get("role"):
            return data
        if not self.access.is_executive:
            committee = self.access.committee
            if committee is None or not committee.is_active:
                raise forms.ValidationError("Your committee is not active, so you cannot make codes for it.")
            data["committee"] = committee

        if role == JoinCode.Role.COMMITTEE_HEAD:
            if committee is None:
                self.add_error("committee", "Pick the committee this Committee Head will lead.")
                return data
            if Membership.objects.filter(organization=self.access.organization, term=self.access.term,
                                         committee=committee, role=Membership.Role.COMMITTEE_HEAD).exists():
                self.add_error("committee", f"{committee.name} already has a Committee Head this A.Y.")
            data["max_uses"] = 1
            if data.get("hours") not in codes.HEAD_EXPIRY_HOURS:
                self.add_error("hours", "A Committee Head code can work for 24 hours at most.")
        else:
            if data.get("hours") not in codes.MEMBER_EXPIRY_HOURS:
                self.add_error("hours", "Choose how long the code should work.")
        return data
