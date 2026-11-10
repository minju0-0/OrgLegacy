from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/events/<int:pk>/logs/add/", views.LogAdd.as_view(), name="eventlog_add"),
    path("<int:org_id>/events/<int:pk>/logs/<int:log_pk>/edit/", views.LogEdit.as_view(), name="eventlog_edit"),
    path("<int:org_id>/events/<int:pk>/logs/<int:log_pk>/delete/", views.LogDelete.as_view(), name="eventlog_delete"),
]
