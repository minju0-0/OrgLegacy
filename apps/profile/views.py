from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.shared.selectors import memberships_for_profile

from .forms import UserDetailsForm


@login_required
def profile_view(request):
    if request.method == "POST":
        user_form = UserDetailsForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        user_form = UserDetailsForm(instance=request.user)

    return render(request, "profile/profile.html", {
        "user_form": user_form,
        "organizations": memberships_for_profile(request.user),
    })
