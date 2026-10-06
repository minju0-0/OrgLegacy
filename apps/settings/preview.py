"""Design preview data for Settings. DEBUG only.

Open /settings/?preview=full  (every future section filled)  or  ?preview=bare  (what you have today).

DELETE THIS FILE, and the lines in views.py that use it, once the real data is wired.
"""
from .preferences import groups

SESSIONS = [
    {"id": 1, "device": "Chrome on Windows", "kind": "desktop", "place": "Cebu City, Philippines", "last_active": "Active now", "current": True},
    {"id": 2, "device": "Safari on iPhone", "kind": "phone", "place": "Cebu City, Philippines", "last_active": "Yesterday, 8:14 PM", "current": False},
    {"id": 3, "device": "Firefox on Ubuntu", "kind": "desktop", "place": "Mandaue, Philippines", "last_active": "3 days ago", "current": False},
]


def preview_context(name):
    if name == "bare":
        return {"preview": "bare"}
    saved = {"approval_result": {"email": True}, "handover_reminder": {"email": False}, "member_joined": {"in_app": False}}
    return {"preview": "full", "sessions": SESSIONS, "two_factor": {"enabled": False},
            "notification_groups": groups(saved)}
