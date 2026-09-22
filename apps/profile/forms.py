from django import forms
from django.contrib.auth.models import User

from apps.accounts.models import Profile


class StyledFormMixin:
    """
    Adds a consistent 'form-input' CSS class and an auto-generated
    placeholder to every field on a form — the same trick
    RegisterForm uses in apps/register/forms.py.

    This is intentionally duplicated in apps/settings/forms.py rather
    than imported from one shared place: it keeps the profile and
    settings apps free to change or drop this styling independently,
    with no cross-app coupling for something this small.
    """

    def _style_fields(self):
        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing_class} form-input".strip()
            if not field.widget.attrs.get('placeholder') and field.label:
                field.widget.attrs['placeholder'] = f"Enter {field.label.lower()}"


class UserDetailsForm(StyledFormMixin, forms.ModelForm):
    """The 'who you are' half of the profile page — fields that live on Django's built-in User model."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ProfileDetailsForm(StyledFormMixin, forms.ModelForm):
    """The OrgLegacy-specific half of the profile page — fields that live on the shared Profile model."""

    class Meta:
        model = Profile
        fields = ['bio', 'avatar_url']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': "e.g. Served as Secretary (2023-2024). Managed committee meeting minutes, supplier directories, and the spring recruitment drive."
            }),
            'avatar_url': forms.TextInput(attrs={
                'placeholder': "https://example.com/photo.jpg"
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
