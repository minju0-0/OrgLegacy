from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/sign-off/", views.SignOffOverview.as_view(), name="signoff_page"),
    path("<int:org_id>/sign-off/initiate/", views.SignOffInitiate.as_view(), name="signoff_initiate"),
    path("<int:org_id>/sign-off/vote/", views.SignOffVote.as_view(), name="signoff_vote"),
    path("<int:org_id>/sign-off/cancel/", views.SignOffCancel.as_view(), name="signoff_cancel"),
]
