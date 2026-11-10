from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/members/", views.MemberList.as_view(), name="member_list"),
    path("<int:org_id>/members/leave/", views.LeaveView.as_view(), name="member_leave"),
    path("<int:org_id>/members/<int:membership_id>/remove/", views.RemoveView.as_view(), name="member_remove"),
]
