from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/join-codes/", views.JoinCodeList.as_view(), name="joincode_list"),
    path("<int:org_id>/join-codes/new/", views.JoinCodeCreate.as_view(), name="joincode_create"),
    path("<int:org_id>/join-codes/quick/", views.JoinCodeQuick.as_view(), name="joincode_quick"),
    path("<int:org_id>/join-codes/<int:pk>/revoke/", views.JoinCodeRevoke.as_view(), name="joincode_revoke"),
]
