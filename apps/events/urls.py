from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/events/", views.EventList.as_view(), name="event_list"),
    path("<int:org_id>/events/new/", views.EventCreate.as_view(), name="event_create"),
    path("<int:org_id>/events/<int:pk>/", views.EventDetail.as_view(), name="event_detail"),
    path("<int:org_id>/events/<int:pk>/edit/", views.EventEdit.as_view(), name="event_edit"),
    path("<int:org_id>/events/<int:pk>/delete/", views.EventDelete.as_view(), name="event_delete"),
]
