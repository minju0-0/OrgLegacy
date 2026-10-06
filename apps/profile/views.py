from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.shared.selectors import memberships_for_profile

from .forms import UserDetailsForm


@login_required
def profile_view(request):
    """Context contract: see docs/PROFILE_SETTINGS.md.

    Real today: user_form, organizations (one dict per seat).
    Optional, supply when real: profile_stats (list of {label, value}), avatar_url (str).
    """
    if request.method == "POST":
        user_form = UserDetailsForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        user_form = UserDetailsForm(instance=request.user)

    seats = memberships_for_profile(request.user)
    context = {"user_form": user_form, "organizations": seats}

    if settings.DEBUG and request.GET.get("preview"):               # design preview, delete with preview.py
        from .preview import PreviewDetailsForm, preview_context
        context.update(preview_context(request.GET["preview"]))
        if context.pop("use_preview_form", False):
            context["user_form"] = PreviewDetailsForm(instance=request.user)
        seats = context["organizations"]

    context["seat_count"] = len(seats)
    context["organization_count"] = len({s["name"] for s in seats})
    return render(request, "profile/profile.html", context)
