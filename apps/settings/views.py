import json

from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.models import EventLog, HandoverNote, Membership, SupplierRating
from apps.shared.http import json_login_required, read_json
from apps.shared.selectors import ay_label

from .forms import AccountDeleteForm, StyledPasswordChangeForm
from .preferences import groups


@login_required
def settings_view(request):
    """
    Account management: change password, or permanently delete the account.
    The page has independent <form> elements; each POST carries a hidden
    'form_name' field so this single view knows which one was submitted.
    """
    password_form = StyledPasswordChangeForm(user=request.user)
    delete_form = AccountDeleteForm()

    if request.method == 'POST':
        form_name = request.POST.get('form_name')

        if form_name == 'change_password':
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed.")
                return redirect('settings')

        elif form_name == 'delete_account':
            delete_form = AccountDeleteForm(request.POST)
            if delete_form.is_valid():
                user = request.user
                logout(request)
                user.delete()
                messages.info(request, "Your account has been permanently deleted.")
                return redirect('login')

    saved_prefs = request.session.get('notification_prefs') or {}
    context = {
        'password_form': password_form,
        'delete_form': delete_form,
        'notification_groups': groups(saved_prefs),
    }

    if dj_settings.DEBUG and request.GET.get('preview'):          # design preview, delete with preview.py
        from .preview import preview_context
        context.update(preview_context(request.GET['preview']))

    return render(request, 'settings/settings.html', context)


@require_POST
@json_login_required
def save_notifications_view(request):
    """Hook settings:save-notifications."""
    data = read_json(request)
    prefs = data.get("prefs") if isinstance(data.get("prefs"), dict) else data
    if not isinstance(prefs, dict):
        prefs = {}
    request.session["notification_prefs"] = prefs
    return JsonResponse({"saved": True})


@require_POST
@json_login_required
def export_request_view(request):
    """Hook account:export. Returns {url} for downloading the user's archive JSON."""
    return JsonResponse({"url": reverse("settings_export_download")})


@login_required
def export_download_view(request):
    """Download a JSON copy of the user's profile, memberships, and authored entries."""
    u = request.user
    memberships = [
        {
            "organization": m.organization.name,
            "academic_year": ay_label(m.term.label),
            "role": m.get_role_display(),
            "committee": m.committee.name if m.committee else "",
            "title": m.title,
        }
        for m in Membership.objects.filter(user=u).select_related("organization", "term", "committee")
    ]
    logs = [
        {
            "event": log.event.title,
            "what_happened": log.what_happened,
            "challenges_lessons": log.challenges_lessons,
            "created_at": log.created_at.isoformat(),
        }
        for log in EventLog.objects.filter(author=u).select_related("event")
    ]
    notes = [
        {
            "organization": n.organization.name,
            "academic_year": ay_label(n.term.label),
            "scope": n.get_scope_display(),
            "content": n.content,
            "created_at": n.created_at.isoformat(),
        }
        for n in HandoverNote.objects.filter(author=u).select_related("organization", "term")
    ]
    ratings = [
        {
            "supplier": r.supplier.name,
            "score": r.score,
            "comment": r.comment,
        }
        for r in SupplierRating.objects.filter(rated_by=u).select_related("supplier")
    ]
    payload = {
        "account": {
            "username": u.username,
            "full_name": u.get_full_name(),
            "email": u.email,
            "date_joined": u.date_joined.isoformat(),
        },
        "memberships": memberships,
        "event_logs": logs,
        "handover_notes": notes,
        "supplier_ratings": ratings,
    }
    response = HttpResponse(
        json.dumps(payload, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="orglegacy-{u.username}-data.json"'
    return response
