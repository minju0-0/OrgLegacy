from django import forms
from django.contrib.auth.forms import PasswordChangeForm


class StyledFormMixin:
    """Adds the shared form-input class and a default placeholder to every field."""

    def _style_fields(self):
        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing_class} form-input".strip()
            if not field.widget.attrs.get('placeholder') and field.label:
                field.widget.attrs['placeholder'] = f"Enter {field.label.lower()}"


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    """Django's built-in password-change form, restyled to match the rest of the app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class AccountDeleteForm(StyledFormMixin, forms.Form):
    """Requires an explicit, deliberate confirmation before an account is deleted."""

    confirm = forms.CharField(
        required=True,
        label="Confirmation",
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'placeholder': 'Type DELETE to confirm'
        }),
        help_text="This authorization cannot be undone."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_confirm(self):
        confirm = self.cleaned_data.get('confirm', '')
        if confirm != 'DELETE':
            raise forms.ValidationError("You must type 'DELETE' exactly to confirm.")
        return confirm
