import base64

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Event, EventLog, HandoverNote, SupplierRating
from apps.shared.http import fail, json_login_required
from apps.shared.selectors import memberships_for_profile

from .forms import UserDetailsForm

MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = ("image/jpeg", "image/png", "image/webp")


@login_required
def profile_view(request):
    """Context contract: see docs/PROFILE_SETTINGS.md.

    Real today: user_form, organizations (one dict per seat), profile_stats, avatar_url.
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
    events_count = Event.objects.filter(created_by=request.user).count()
    logs_count = EventLog.objects.filter(author=request.user).count()
    notes_count = HandoverNote.objects.filter(author=request.user).count()
    ratings_count = SupplierRating.objects.filter(rated_by=request.user).count()

    profile_stats = []
    if seats or events_count or logs_count or notes_count or ratings_count:
        profile_stats = [
            {"label": "Events planned", "value": events_count},
            {"label": "Event logs", "value": logs_count},
            {"label": "Handover notes", "value": notes_count},
        ]

    context = {
        "user_form": user_form,
        "organizations": seats,
        "profile_stats": profile_stats,
        "avatar_url": request.session.get("avatar_url"),
    }

    if settings.DEBUG and request.GET.get("preview"):               # design preview, delete with preview.py
        from .preview import PreviewDetailsForm, preview_context
        context.update(preview_context(request.GET["preview"]))
        if context.pop("use_preview_form", False):
            context["user_form"] = PreviewDetailsForm(instance=request.user)
        seats = context["organizations"]

    context["seat_count"] = len(seats)
    context["organization_count"] = len({s["name"] for s in seats})
    return render(request, "profile/profile.html", context)


@require_POST
@json_login_required
def avatar_save_view(request):
    """Hook profile:avatar-save."""
    f = request.FILES.get("avatar")
    if not f:
        return fail("Choose a photo first.")
    if f.content_type not in ALLOWED_AVATAR_TYPES:
        return fail("Use a JPG, PNG or WebP photo.")
    if f.size > MAX_AVATAR_BYTES:
        return fail("The limit is 2 MB.")
    encoded = base64.b64encode(f.read()).decode("ascii")
    data_url = f"data:{f.content_type};base64,{encoded}"
    request.session["avatar_url"] = data_url
    return JsonResponse({"avatar_url": data_url})


@require_POST
@json_login_required
def avatar_remove_view(request):
    """Hook profile:avatar-remove."""
    request.session.pop("avatar_url", None)
    return JsonResponse({"removed": True})
