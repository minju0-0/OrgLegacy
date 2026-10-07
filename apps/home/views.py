from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.shared.selectors import activity_for_home, attention_for_home, organizations_for_home


@login_required
def home_view(request):
    """Context contract for the Home screen: see docs/HOME.md.

    Real data today: `organizations` (with each Executive's share code), `attention` (join codes about to
    expire), `activity` (recent seats), and the bell (`notifications`, from apps.notifications.context).
    Home only displays. Every button's logic lives in the slice that owns it: org:create in organizations,
    join:* in join, share:regenerate in joincodes, org:leave-confirm in members (see the scripts below).
    """
    context = {
        "organizations": organizations_for_home(request.user),
        "attention": attention_for_home(request.user),
        "activity": activity_for_home(request.user),
        "show_attention": True,
        "home_state": "ready",
    }

    if settings.DEBUG and request.GET.get("preview"):              # design preview, delete with preview.py
        from .preview import preview_context
        context.update(preview_context(request.GET["preview"]))

    return render(request, "home/home.html", context)
