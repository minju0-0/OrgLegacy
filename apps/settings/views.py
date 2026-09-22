from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AccountDeleteForm, StyledPasswordChangeForm


@login_required
def settings_view(request):
    """
    Account security and management: change password, or permanently
    delete the account. This page has two independent <form> elements;
    each POST carries a hidden 'form_name' field so this single view
    knows which one was submitted.
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
                return redirect('settings:settings')

        elif form_name == 'delete_account':
            delete_form = AccountDeleteForm(request.POST)
            if delete_form.is_valid():
                user = request.user
                logout(request)
                user.delete()  # cascades to accounts.Profile via on_delete=CASCADE
                messages.info(request, "Your account has been permanently deleted.")
                return redirect('login:login')

    return render(request, 'settings/settings.html', {
        'password_form': password_form,
        'delete_form': delete_form,
    })
