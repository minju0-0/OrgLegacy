from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AccountDeleteForm, StyledPasswordChangeForm
from .preferences import groups


@login_required
def settings_view(request):
    """
    Account management: change password, or permanently delete the account.
    The page has independent <form> elements; each POST carries a hidden
    'form_name' field so this single view knows which one was submitted.
    Notification preferences, sessions, two-step sign-in and data export are
    designed but not stored yet: they connect through data-action hooks.
    """
    password_form = StyledPasswordChangeForm(user=request.user)
    delete_form = AccountDeleteForm()

    if request.method == 'POST':
        form_name = request.POST.get('form_name')

        if form_name == 'change_password':
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Changing the password rotates Django's session auth hash;
                # without this the user would be silently logged out.
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed.")
                return redirect('settings')

        elif form_name == 'delete_account':
            delete_form = AccountDeleteForm(request.POST)
            if delete_form.is_valid():
                user = request.user
                logout(request)
                user.delete()  # cascades to accounts.Profile via on_delete=CASCADE
                messages.info(request, "Your account has been permanently deleted.")
                return redirect('login')

    context = {
        'password_form': password_form,
        'delete_form': delete_form,
        'notification_groups': groups(),          # catalog with defaults; pass saved values to groups() later
    }
    # Optional, supply when real: sessions (list), two_factor ({'enabled': bool}). See docs/PROFILE_SETTINGS.md.

    if dj_settings.DEBUG and request.GET.get('preview'):          # design preview, delete with preview.py
        from .preview import preview_context
        context.update(preview_context(request.GET['preview']))

    return render(request, 'settings/settings.html', context)
