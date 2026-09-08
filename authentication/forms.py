from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class RegisterForm(UserCreationForm):
    """
    Registration form for OrgLegacy. Collects the base Django User
    fields (username/password) plus the OrgLegacy-specific profile
    fields (role, organization, student status) so a single sign-up
    step creates both the account and its role assignment.
    """
    email = forms.EmailField(required=True, help_text="Use your institutional email.")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing_class} form-input".strip()
            if not field.widget.attrs.get('placeholder') and field.label:
                field.widget.attrs['placeholder'] = f"Enter {field.label.lower()}"

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(
                user=user,
                organization_name='',
                student_status='',
            )
        return user
