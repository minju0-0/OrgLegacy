from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/committees/", views.CommitteeList.as_view(), name="committee_list"),
    path("<int:org_id>/committees/add/", views.CommitteeCreate.as_view(), name="committee_create"),
    path("<int:org_id>/committees/<int:pk>/rename/", views.CommitteeRename.as_view(), name="committee_rename"),
    path("<int:org_id>/committees/<int:pk>/toggle/", views.CommitteeToggle.as_view(), name="committee_toggle"),
]
