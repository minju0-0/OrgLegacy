from django import forms

from apps.accounts.models import Committee


class CommitteeForm(forms.Form):
    """One field, used to add a committee and to rename one."""
    name = forms.CharField(
        label="Committee name", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Logistics", "autocomplete": "off"}),
        error_messages={"required": "Give the committee a name."},
    )

    def __init__(self, *args, organization, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization, self.instance = organization, instance

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Give the committee a name.")
        taken = Committee.objects.filter(organization=self.organization, name__iexact=name)
        if self.instance:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("This organization already has a committee with that name.")
        return name
