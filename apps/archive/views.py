"""Searchable Institutional Memory Archive (Phase 7).

Cross-cutting search across historical events, suppliers, and handover notes,
filterable by academic year and content type, plus the global topbar JSON search.
"""
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Event, HandoverNote, Membership, Organization, Supplier, Term
from apps.shared.permissions import LIVE, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

STATUS_LABEL = {
    Term.Status.ACTIVE: "Active",
    Term.Status.PENDING_SIGNOFF: "Awaiting approval",
    Term.Status.CLOSED: "Closed",
}


class ArchiveSearch(OrgRoleRequiredMixin, TemplateView):
    template_name = "archive/archive.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        org = access.organization

        q = (self.request.GET.get("q") or "").strip()
        kind = (self.request.GET.get("kind") or "all").lower()
        term_filter = self.request.GET.get("term") or ""

        if access.term.status in LIVE:
            terms_qs = org.terms.filter(Q(pk=access.term.pk) | Q(status=Term.Status.CLOSED))
        else:
            served_ids = Membership.objects.filter(user=self.request.user, organization=org).values("term_id")
            terms_qs = org.terms.filter(pk__in=served_ids)

        terms = list(terms_qs.order_by("-start_date", "-pk"))
        allowed_term_ids = {t.pk for t in terms}

        term_options = [{"id": "", "label": "All academic years"}] + [
            {"id": str(t.pk), "label": f"{ay_label(t.label)} ({STATUS_LABEL.get(t.status, t.status)})"}
            for t in terms
        ]

        results = []
        counts = {"events": 0, "suppliers": 0, "notes": 0}

        events_qs = Event.objects.filter(organization=org, term_id__in=allowed_term_ids).select_related("term", "committee")
        suppliers_qs = Supplier.objects.filter(organization=org)
        notes_qs = HandoverNote.objects.filter(organization=org, term_id__in=allowed_term_ids).select_related("term", "committee", "author")

        if term_filter.isdigit() and int(term_filter) in allowed_term_ids:
            events_qs = events_qs.filter(term_id=int(term_filter))
            notes_qs = notes_qs.filter(term_id=int(term_filter))

        if q:
            if kind in ("all", "events"):
                ev_matches = events_qs.filter(
                    Q(title__icontains=q)
                    | Q(description__icontains=q)
                    | Q(logs__what_happened__icontains=q)
                    | Q(logs__challenges_lessons__icontains=q)
                ).distinct()
                for e in ev_matches[:20]:
                    results.append({
                        "kind": "event",
                        "title": e.title,
                        "snippet": e.description,
                        "date": e.date,
                        "ay": ay_label(e.term.label),
                        "url": reverse("event_detail", args=[org.pk, e.pk]),
                        "meta": e.committee.name if e.committee else "Whole organization",
                    })

            if kind in ("all", "suppliers"):
                sup_matches = suppliers_qs.filter(
                    Q(name__icontains=q)
                    | Q(contact_info__icontains=q)
                    | Q(cost_notes__icontains=q)
                    | Q(ratings__comment__icontains=q)
                ).distinct()
                for s in sup_matches[:20]:
                    results.append({
                        "kind": "supplier",
                        "title": s.name,
                        "snippet": s.contact_info or s.cost_notes,
                        "date": None,
                        "ay": "Directory",
                        "url": reverse("supplier_detail", args=[org.pk, s.pk]),
                        "meta": s.cost_notes[:60] if s.cost_notes else "Supplier",
                    })

            if kind in ("all", "notes"):
                note_matches = notes_qs.filter(Q(content__icontains=q)).distinct()
                for n in note_matches[:20]:
                    results.append({
                        "kind": "note",
                        "title": f"{n.committee.name if n.committee else 'Organization'} Handover Note",
                        "snippet": n.content,
                        "date": n.created_at.date() if n.created_at else None,
                        "ay": ay_label(n.term.label),
                        "url": reverse("handover_detail", args=[org.pk, n.pk]),
                        "meta": f"By {n.author.get_full_name() or n.author.username}",
                    })

        counts["events"] = Event.objects.filter(organization=org, term_id__in=allowed_term_ids).count()
        counts["suppliers"] = Supplier.objects.filter(organization=org).count()
        counts["notes"] = HandoverNote.objects.filter(organization=org, term_id__in=allowed_term_ids).count()
        counts["terms"] = len(terms)

        context.update({
            "access": access,
            "organization": org,
            "term": access.term,
            "ay": ay_label(access.term.label),
            "org_nav": org_nav(access),
            "active_page": "archive_search",
            "q": q,
            "kind": kind,
            "selected_term": term_filter,
            "term_options": term_options,
            "results": results,
            "total_results": len(results),
            "counts": counts,
        })
        return context


class GlobalSearchView(View):
    """Topbar search endpoint: GET /search/?q=... -> JSON groups for OL.search.connect."""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse([], safe=False, status=401)

        q = (request.GET.get("q") or "").strip()
        if len(q) < 2:
            return JsonResponse([], safe=False)

        memberships = list(
            Membership.objects.filter(user=request.user)
            .select_related("organization", "term")
        )
        if not memberships:
            return JsonResponse([], safe=False)

        org_ids = {m.organization_id for m in memberships}
        live_org_ids = {m.organization_id for m in memberships if m.term.status in LIVE}
        served_term_ids = {m.term_id for m in memberships}

        term_q = Q(term_id__in=served_term_ids) | Q(
            organization_id__in=live_org_ids, term__status=Term.Status.CLOSED
        )

        groups = []

        # 1. Organizations
        orgs = Organization.objects.filter(pk__in=org_ids).filter(
            Q(name__icontains=q) | Q(acronym__icontains=q)
        ).order_by("name")[:5]
        if orgs:
            groups.append({
                "label": "Organizations",
                "items": [
                    {
                        "id": o.pk,
                        "title": o.name,
                        "meta": o.acronym or "Organization",
                        "href": reverse("organization_detail", args=[o.pk]),
                    }
                    for o in orgs
                ],
            })

        # 2. Events
        events = (
            Event.objects.filter(organization_id__in=org_ids)
            .filter(term_q)
            .filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(logs__what_happened__icontains=q)
                | Q(logs__challenges_lessons__icontains=q)
            )
            .select_related("organization", "term")
            .distinct()
            .order_by("-date", "-pk")[:5]
        )
        if events:
            groups.append({
                "label": "Events",
                "items": [
                    {
                        "id": e.pk,
                        "title": e.title,
                        "meta": f"{e.organization.acronym or e.organization.name}, {ay_label(e.term.label)}",
                        "href": reverse("event_detail", args=[e.organization_id, e.pk]),
                    }
                    for e in events
                ],
            })

        # 3. Suppliers
        suppliers = (
            Supplier.objects.filter(organization_id__in=org_ids)
            .filter(
                Q(name__icontains=q)
                | Q(contact_info__icontains=q)
                | Q(cost_notes__icontains=q)
                | Q(ratings__comment__icontains=q)
            )
            .select_related("organization")
            .distinct()
            .order_by("name")[:5]
        )
        if suppliers:
            groups.append({
                "label": "Suppliers",
                "items": [
                    {
                        "id": s.pk,
                        "title": s.name,
                        "meta": f"{s.organization.acronym or s.organization.name} supplier",
                        "href": reverse("supplier_detail", args=[s.organization_id, s.pk]),
                    }
                    for s in suppliers
                ],
            })

        # 4. Handover notes
        notes = (
            HandoverNote.objects.filter(organization_id__in=org_ids)
            .filter(term_q)
            .filter(Q(content__icontains=q) | Q(committee__name__icontains=q))
            .select_related("organization", "term", "committee")
            .distinct()
            .order_by("-created_at", "-pk")[:5]
        )
        if notes:
            groups.append({
                "label": "Handover notes",
                "items": [
                    {
                        "id": n.pk,
                        "title": f"{n.committee.name if n.committee else 'Organization'} handover",
                        "meta": f"{n.organization.acronym or n.organization.name}, {ay_label(n.term.label)}",
                        "href": reverse("handover_detail", args=[n.organization_id, n.pk]),
                    }
                    for n in notes
                ],
            })

        return JsonResponse(groups, safe=False)
