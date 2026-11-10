from django import forms

from apps.accounts.models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_info", "cost_notes"]
        labels = {"name": "Supplier name", "contact_info": "How to reach them", "cost_notes": "Prices and cost notes"}
        help_texts = {"contact_info": "Contact person, phone, email, page or address.",
                      "cost_notes": "What they charged, minimum orders, discounts. Next year's treasurer will look here."}
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "autocomplete": "off", "placeholder": "Happy Prints Cebu"}),
            "contact_info": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "cost_notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }
        error_messages = {"name": {"required": "Give the supplier a name."},
                          "contact_info": {"required": "Add at least one way to reach them."}}

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Give the supplier a name.")
        same = Supplier.objects.filter(organization=self.organization, name__iexact=name).exclude(pk=self.instance.pk)
        if same.exists():
            raise forms.ValidationError("This organization already lists a supplier with that name.")
        return name

    def clean_contact_info(self):
        text = self.cleaned_data["contact_info"].strip()
        if not text:
            raise forms.ValidationError("Add at least one way to reach them.")
        return text
