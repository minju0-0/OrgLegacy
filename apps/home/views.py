from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.shared.selectors import organizations_for_home


@login_required
def home_view(request):
    """Context contract for the Home screen: see docs/HOME.md.

    Real data today: `organizations`. Everything else is optional and the template
    degrades without it: attention, activity, show_attention, show_activity,
    notifications, notifications_unread, home_state ('ready' | 'loading' | 'error').
    """
    context = {"organizations": organizations_for_home(request.user), "home_state": "ready"}

    if settings.DEBUG and request.GET.get("preview"):              # design preview, delete with preview.py
        from .preview import preview_context
        context.update(preview_context(request.GET["preview"]))

    return render(request, "home/home.html", context)
