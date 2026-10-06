"""The catalog of notifications a person can choose to receive.

This is product definition, not storage. `groups()` merges the catalog with whatever
the person has saved. Nothing is saved yet, so every toggle starts at its default.
When you add storage, pass the saved values as {key: {"in_app": bool, "email": bool}}.
A channel set to None means "not offered" and shows a dash instead of a switch.
"""

CATALOG = [
    {"label": "Approvals", "items": [
        {"key": "approval_requested", "label": "An A.Y. needs your approval",
         "help": "Sent to executives when officers ask to close an A.Y.", "in_app": True, "email": True},
        {"key": "approval_result", "label": "An A.Y. is approved and closed",
         "help": "", "in_app": True, "email": False},
    ]},
    {"label": "Handover", "items": [
        {"key": "handover_received", "label": "Someone writes a handover note for you",
         "help": "", "in_app": True, "email": True},
        {"key": "handover_reminder", "label": "A reminder to write your own handover note",
         "help": "Sent before an A.Y. closes.", "in_app": True, "email": True},
    ]},
    {"label": "People", "items": [
        {"key": "member_joined", "label": "Someone joins with your join code",
         "help": "", "in_app": True, "email": False},
        {"key": "role_changed", "label": "Your role changes",
         "help": "", "in_app": True, "email": True},
    ]},
    {"label": "Summary", "items": [
        {"key": "weekly_digest", "label": "A weekly summary of what was added",
         "help": "One email a week.", "in_app": None, "email": False},
    ]},
]


def groups(saved=None):
    saved = saved or {}
    out = []
    for g in CATALOG:
        items = []
        for it in g["items"]:
            item = dict(it)
            for ch in ("in_app", "email"):
                if item[ch] is not None and ch in saved.get(it["key"], {}):
                    item[ch] = bool(saved[it["key"]][ch])
            items.append(item)
        out.append({"label": g["label"], "items": items})
    return out
