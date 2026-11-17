from django import forms

from apps.accounts.models import Committee, HandoverNote
from apps.shared.permissions import EXECUTIVE, HEAD


class HandoverNoteForm(forms.ModelForm):
    class Meta:
        model = HandoverNote
        fields = ["scope", "committee", "content"]
        labels = {
            "scope": "Note scope",
            "committee": "Committee",
            "content": "Transition guidance & handover record",
        }
        help_texts = {
            "scope": "Organization-wide guidance, or committee-specific lessons.",
            "committee": "Which committee this handover note guides.",
            "content": "Write down what the next officers must know: workflows, credentials, recurring challenges, and operational advice.",
        }
        widgets = {
            "scope": forms.Select(attrs={"class": "form-input"}),
            "committee": forms.Select(attrs={"class": "form-input"}),
            "content": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 8,
                "placeholder": "What worked well, what caused delays, contacts to keep, and key operational advice for incoming officers...",
            }),
        }

    def __init__(self, *args, access, **kwargs):
        super().__init__(*args, **kwargs)
        self.access = access
        org = access.organization
        committees = Committee.objects.filter(organization=org, is_active=True).order_by("name")
        self.fields["committee"].queryset = committees
        self.fields["committee"].required = False

        if access.role == HEAD:
            self.fields["scope"].choices = [(HandoverNote.Scope.COMMITTEE, "Committee")]
            self.fields["scope"].initial = HandoverNote.Scope.COMMITTEE
            if access.committee:
                self.fields["committee"].queryset = Committee.objects.filter(pk=access.committee.pk)
                self.fields["committee"].initial = access.committee
        else:
            self.fields["scope"].choices = HandoverNote.Scope.choices

    def clean(self):
        cleaned = super().clean()
        scope = cleaned.get("scope")
        committee = cleaned.get("committee")

        if self.access.role == HEAD:
            scope = HandoverNote.Scope.COMMITTEE
            committee = self.access.committee
            cleaned["scope"] = scope
            cleaned["committee"] = committee
            if "committee" in self._errors:
                del self._errors["committee"]

        if scope == HandoverNote.Scope.COMMITTEE:
            if not committee:
                self.add_error("committee", "Pick the committee this handover note applies to.")
        elif scope == HandoverNote.Scope.ORGANIZATION:
            cleaned["committee"] = None

        content = (cleaned.get("content") or "").strip()
        if not content:
            self.add_error("content", "Write what the incoming officers need to know.")
        elif len(content) > 10000:
            self.add_error("content", "Keep the note under 10,000 characters.")
        cleaned["content"] = content

        return cleaned
