"""Design preview data for the Home screen.

DEBUG only. Open /home/?preview=full  |  clear  |  tasks  |  light  |  uneven  |  few  |  empty  |  loading  |  error
to review every state of the screen with realistic sample data.

DELETE THIS FILE, and the two lines in views.py that import and call it,
once the real data is wired. Nothing else depends on it.
"""
from types import SimpleNamespace as P


def _people(names):
    return [P(username=n) for n in names]


def _org(i, name, acronym, role, role_code, ay, status, count, *, title="", committee="",
         counts=None, last="", code="", expires=""):
    return {
        "id": i, "name": name, "acronym": acronym, "role": role, "role_code": role_code,
        "title": title, "committee": committee, "ay": ay, "status": status,
        "member_count": count, "members": _people(["Ana", "Jun", "Mika"][: min(count, 3)]),
        "url": None,
        "counts": counts,                 # {"events": int, "suppliers": int, "notes": int}
        "last_activity": last,            # short human string
        "can_share_code": role_code == "EXECUTIVE" and status != "CLOSED",
        "join_code": code, "join_code_expires": expires,
    }


ORGS = [
    _org(1, "Junior Philippine Computer Society", "JPCS", "Executive", "EXECUTIVE", "A.Y. 2026-2027", "ACTIVE", 12,
         title="Treasurer", counts={"events": 14, "suppliers": 6, "notes": 3}, last="Active 2 hours ago",
         code="4F7K92QD", expires="Expires 12 Oct"),
    _org(2, "CIT Debate Society", "CDS", "Committee Head", "COMMITTEE_HEAD", "A.Y. 2026-2027", "PENDING_SIGNOFF", 8,
         committee="Logistics", counts={"events": 9, "suppliers": 4, "notes": 2}, last="Active yesterday"),
    _org(3, "Rotaract Club of Cebu Tech", "RCCT", "Executive", "EXECUTIVE", "A.Y. 2025-2026", "PENDING_SIGNOFF", 24,
         title="President", counts={"events": 31, "suppliers": 12, "notes": 8}, last="Active 3 days ago"),
    _org(4, "CIT Student Council", "CSC", "Member", "MEMBER", "A.Y. 2026-2027", "ACTIVE", 41,
         committee="Events", counts={"events": 22, "suppliers": 11, "notes": 5}, last="Active 5 days ago"),
    _org(5, "Culture and Arts Guild", "CAG", "Member", "MEMBER", "A.Y. 2025-2026", "CLOSED", 17,
         committee="Production", counts={"events": 18, "suppliers": 7, "notes": 6}, last="Closed 31 May 2026"),
    _org(6, "Mathematics Society", "MATHSOC", "Committee Head", "COMMITTEE_HEAD", "A.Y. 2025-2026", "CLOSED", 15,
         committee="Academics", counts={"events": 11, "suppliers": 3, "notes": 4}, last="Closed 31 May 2026"),
]

ATTENTION = [
    {"id": 1, "kind": "approval", "title": "Approve A.Y. 2025-2026", "org": "Rotaract Club of Cebu Tech",
     "ay": "A.Y. 2025-2026", "stamp": "Awaiting approval", "due": "Due 15 Jun", "action": "Review", "url": None},
    {"id": 2, "kind": "handover", "title": "Write your handover note", "org": "CIT Debate Society",
     "ay": "A.Y. 2026-2027", "due": "Due 31 May", "action": "Write note", "url": None},
    {"id": 3, "kind": "event", "title": "Add a budget to Freshmen welcome", "org": "Junior Philippine Computer Society",
     "ay": "A.Y. 2026-2027", "action": "Add budget", "url": None},
    {"id": 4, "kind": "invite", "title": "Your join code expires in 3 days", "org": "Junior Philippine Computer Society",
     "ay": "A.Y. 2026-2027", "action": "Make a new code", "url": None},
    {"id": 5, "kind": "note", "title": "Read the handover note from Kai", "org": "CIT Student Council",
     "ay": "A.Y. 2026-2027", "action": "Read", "url": None},
    {"id": 6, "kind": "event", "title": "Add a venue to Foundation day booth", "org": "CIT Student Council",
     "ay": "A.Y. 2026-2027", "due": "Due 20 Oct", "action": "Add venue", "url": None},
    {"id": 7, "kind": "note", "title": "Read the handover note from Mika", "org": "CIT Debate Society",
     "ay": "A.Y. 2026-2027", "action": "Read", "url": None},
]

ACTIVITY = [
    {"id": 1, "actor": "Ana Reyes", "text": "added the event Leadership summit", "org": "JPCS", "ay": "A.Y. 2026-2027", "ago": "2h ago"},
    {"id": 2, "actor": "Jun Dela Cruz", "text": "rated the supplier Print Hub 4 out of 5", "org": "CSC", "ay": "A.Y. 2026-2027", "ago": "5h ago"},
    {"id": 3, "actor": "Kai Santos", "text": "wrote a handover note for Logistics", "org": "CDS", "ay": "A.Y. 2026-2027", "ago": "Yesterday"},
    {"id": 4, "actor": "Bea Lim", "text": "asked for approval to close A.Y. 2025-2026", "org": "RCCT", "ay": "A.Y. 2025-2026", "ago": "2 days ago"},
    {"id": 5, "actor": "Leo Tan", "text": "joined with a join code", "org": "JPCS", "ay": "A.Y. 2026-2027", "ago": "3 days ago"},
    {"id": 6, "actor": "Mika Cruz", "text": "added the supplier Cebu Sound Rentals", "org": "CSC", "ay": "A.Y. 2026-2027", "ago": "5 days ago"},
    {"id": 7, "actor": "Rhea Go", "text": "added the event Foundation day booth", "org": "CSC", "ay": "A.Y. 2026-2027", "ago": "6 days ago"},
    {"id": 8, "actor": "Paolo Uy", "text": "edited the supplier Print Hub", "org": "CSC", "ay": "A.Y. 2026-2027", "ago": "1 week ago"},
]

NOTIFICATIONS = [
    {"id": 1, "text": "Bea Lim asked you to approve A.Y. 2025-2026.", "org": "Rotaract Club of Cebu Tech", "ago": "2 days ago", "unread": True, "url": None},
    {"id": 2, "text": "Kai Santos wrote a handover note for you.", "org": "CIT Student Council", "ago": "3 days ago", "unread": True, "url": None},
    {"id": 3, "text": "Leo Tan joined with your join code.", "org": "Junior Philippine Computer Society", "ago": "3 days ago", "unread": False, "url": None},
    {"id": 4, "text": "A.Y. 2025-2026 was closed.", "org": "Culture and Arts Guild", "ago": "31 May", "unread": False, "url": None},
]


def preview_context(name):
    """Context overrides for a preview state. Unknown names fall back to 'full'."""
    base = {"preview": name, "home_state": "ready", "show_attention": True, "show_activity": True,
            "notifications": NOTIFICATIONS, "notifications_unread": 2}
    if name == "clear":     # nothing needs you, but there is activity: strip, then the feed full width
        return {**base, "organizations": ORGS, "attention": [], "activity": ACTIVITY}
    if name == "tasks":     # tasks, but no activity yet: attention alone, full width
        return {**base, "organizations": ORGS, "attention": ATTENTION, "activity": []}
    if name == "light":     # a little of each: split, compact
        return {**base, "organizations": ORGS, "attention": ATTENTION[:1], "activity": ACTIVITY[:2]}
    if name == "uneven":    # 2 tasks beside a full feed: blank ledger lines fill the shorter panel
        return {**base, "organizations": ORGS, "attention": ATTENTION[:2], "activity": ACTIVITY}
    if name == "few":
        return {**base, "organizations": ORGS[:2], "attention": [], "activity": [], "notifications": [], "notifications_unread": 0}
    if name == "empty":
        return {**base, "organizations": [], "attention": [], "activity": [], "show_activity": False, "notifications": [], "notifications_unread": 0}
    if name in ("loading", "error"):
        return {**base, "organizations": [], "attention": [], "activity": [], "home_state": name, "notifications": [], "notifications_unread": 0}
    return {**base, "preview": "full", "organizations": ORGS, "attention": ATTENTION, "activity": ACTIVITY}
