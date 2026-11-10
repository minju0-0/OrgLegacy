from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/suppliers/", views.SupplierList.as_view(), name="supplier_list"),
    path("<int:org_id>/suppliers/add/", views.SupplierCreate.as_view(), name="supplier_create"),
    path("<int:org_id>/suppliers/<int:pk>/", views.SupplierDetail.as_view(), name="supplier_detail"),
    path("<int:org_id>/suppliers/<int:pk>/edit/", views.SupplierEdit.as_view(), name="supplier_edit"),
    path("<int:org_id>/suppliers/<int:pk>/delete/", views.SupplierDelete.as_view(), name="supplier_delete"),
]
