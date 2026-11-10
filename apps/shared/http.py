"""Small helpers for the JSON endpoints the Home screen's data-action hooks call.

Every endpoint answers {"error": "..."} with a 4xx status when it refuses. The browser helper
OL.post (static/js/shared/core.js) turns that into an Error whose message the dialog shows.
"""
import json
from functools import wraps

from django.http import JsonResponse


def wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def read_json(request):
    """The request body as a dict. Anything unreadable becomes an empty dict, never an exception."""
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def fail(message, status=400):
    return JsonResponse({"error": message}, status=status)


def json_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return fail("Log in again to continue.", 401)
        return view(request, *args, **kwargs)
    return wrapped
