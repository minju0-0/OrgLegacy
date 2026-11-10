"""Suppliers: the organization's vendor directory. Everyone in the organization reads it; Executives keep it.

A supplier belongs to the organization, not to one A.Y., so it outlives the officers who found it. That is the
point of the directory. Rating a supplier is the `ratings` slice; this slice only displays the ratings it holds.

  read    any member (an alumnus reads it too)
  keep    Executives: add, edit, delete, in an ACTIVE A.Y.   ("Manages ... vendor records", plan section 3)
"""
from django.contrib import messages
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import Supplier, SupplierRating
from apps.shared.permissions import EXECUTIVE, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label

from .forms import SupplierForm


def base_context(access, **extra):
    context = {"access": access, "organization": access.organization, "term": access.term, "ay": ay_label(access.term.label),
               "org_nav": org_nav(access), "active_page": "supplier_list",
               "can_manage": access.is_executive and access.is_open}
    context.update(extra)
    return context


def directory(access):
    qs = (Supplier.objects.filter(organization=access.organization)
          .annotate(average=Avg("ratings__score"), votes=Count("ratings")).order_by("name"))
    return list(qs)


def detail_context(access, user, supplier, **extra):
    ratings = list(supplier.ratings.select_related("rated_by").order_by("-pk"))
    scores = [r.score for r in ratings]
    mine = next((r for r in ratings if r.rated_by_id == user.pk), None)
    return base_context(access, supplier=supplier, ratings=ratings, votes=len(scores),
                        average=(sum(scores) / len(scores)) if scores else None, my_rating=mine,
                        can_rate=access.is_open, score_choices=[(5, "Excellent"), (4, "Good"), (3, "Fine"), (2, "Poor"), (1, "Avoid")],
                        edit_form=SupplierForm(instance=supplier, organization=access.organization), **extra)


def own_supplier(access, pk):
    return get_object_or_404(Supplier, pk=pk, organization=access.organization)


class SupplierList(OrgRoleRequiredMixin, TemplateView):
    template_name = "suppliers/suppliers.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        context.update(base_context(access), suppliers=directory(access))
        if access.is_executive and access.is_open:
            context["form"] = SupplierForm(organization=access.organization)
        return context


class SupplierDetail(OrgRoleRequiredMixin, View):
    def get(self, request, org_id, pk):
        supplier = own_supplier(self.access, pk)
        return render(request, "suppliers/supplier_detail.html", detail_context(self.access, request.user, supplier))


class Keeper(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True


class SupplierCreate(Keeper):
    def get(self, request, org_id):
        return redirect(reverse("supplier_list", args=[self.access.organization.pk]))

    def post(self, request, org_id):
        form = SupplierForm(request.POST, organization=self.access.organization)
        if not form.is_valid():
            context = base_context(self.access, suppliers=directory(self.access), form=form, open_dialog="supplier-add-modal")
            return render(request, "suppliers/suppliers.html", context, status=400)
        supplier = form.save(commit=False)
        supplier.organization = self.access.organization
        supplier.save()
        messages.success(request, f"{supplier.name} is in the directory.")
        return redirect(reverse("supplier_detail", args=[self.access.organization.pk, supplier.pk]))


class SupplierEdit(Keeper):
    def get(self, request, org_id, pk):
        return redirect(reverse("supplier_detail", args=[self.access.organization.pk, pk]))

    def post(self, request, org_id, pk):
        supplier = own_supplier(self.access, pk)
        form = SupplierForm(request.POST, instance=supplier, organization=self.access.organization)
        if not form.is_valid():
            supplier = own_supplier(self.access, pk)    # the bound form touched the instance; show the saved values
            context = detail_context(self.access, request.user, supplier, open_dialog="supplier-edit-modal")
            context["edit_form"] = form
            return render(request, "suppliers/supplier_detail.html", context, status=400)
        form.save()
        messages.success(request, f"{supplier.name} was updated.")
        return redirect(reverse("supplier_detail", args=[self.access.organization.pk, supplier.pk]))


class SupplierDelete(Keeper):
    def post(self, request, org_id, pk):
        supplier = own_supplier(self.access, pk)
        name, count = supplier.name, supplier.ratings.count()
        supplier.delete()
        extra = f" Its {count} rating{'s' if count != 1 else ''} went with it." if count else ""
        messages.success(request, f"{name} was removed from the directory.{extra}")
        return redirect(reverse("supplier_list", args=[self.access.organization.pk]))
