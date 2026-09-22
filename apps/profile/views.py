from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import Profile

from .forms import ProfileDetailsForm, UserDetailsForm


@login_required
def profile_view(request):
    """
    View and edit a profile. Two ModelForms are shown on one page and
    submitted together: UserDetailsForm (name/email, on the built-in
    User model) and ProfileDetailsForm (bio/avatar, on the shared
    accounts.Profile model). Both must be valid before either is saved.

    get_or_create is used instead of request.user.profile because not
    every User is guaranteed to have one — RegisterForm.save() creates
    it during normal sign-up, but a superuser made with `createsuperuser`
    bypasses that entirely and would otherwise crash this page.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserDetailsForm(request.POST, instance=request.user)
        profile_form = ProfileDetailsForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile:profile')
    else:
        user_form = UserDetailsForm(instance=request.user)
        profile_form = ProfileDetailsForm(instance=profile)

    return render(request, 'profile/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })
