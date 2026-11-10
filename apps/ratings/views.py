"""Ratings: a member scores a supplier from 1 to 5, with an optional comment.

One rating per person per supplier. Rating again replaces your own, so a vendor's average is never padded.
The supplier page (apps/suppliers) draws the form and the list; this slice only takes the submission.
Anyone with a seat in an ACTIVE A.Y. may rate; an alumnus can read ratings but not add one.
"""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.accounts.models import Supplier, SupplierRating
from apps.shared.permissions import OrgRoleRequiredMixin

COMMENT_MAX = 1000


class RateSupplier(OrgRoleRequiredMixin, View):
    require_open_term = True

    def post(self, request, org_id, pk):
        supplier = get_object_or_404(Supplier, pk=pk, organization=self.access.organization)
        back = redirect(reverse("supplier_detail", args=[self.access.organization.pk, supplier.pk]))
        try:
            score = int(request.POST.get("score", ""))
        except ValueError:
            score = 0
        comment = (request.POST.get("comment") or "").strip()
        if not 1 <= score <= 5:
            messages.error(request, "Pick a score from 1 to 5.")
            return back
        if len(comment) > COMMENT_MAX:
            messages.error(request, f"Keep the comment under {COMMENT_MAX} characters.")
            return back

        with transaction.atomic():
            Supplier.objects.select_for_update().get(pk=supplier.pk)       # two quick submissions cannot both insert
            _, created = SupplierRating.objects.update_or_create(
                supplier=supplier, rated_by=request.user, defaults={"score": score, "comment": comment})
        messages.success(request, f"Your rating of {supplier.name} was saved." if created else f"Your rating of {supplier.name} was updated.")
        return back
