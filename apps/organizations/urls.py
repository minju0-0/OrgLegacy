from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.create_view, name="organization_create"),
    path("<int:org_id>/", views.OrganizationPage.as_view(), name="organization_detail"),
]
