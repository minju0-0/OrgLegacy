from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/handover-notes/", views.NoteList.as_view(), name="handover_list"),
    path("<int:org_id>/handover-notes/add/", views.NoteCreate.as_view(), name="handover_add"),
    path("<int:org_id>/handover-notes/<int:pk>/", views.NoteDetail.as_view(), name="handover_detail"),
    path("<int:org_id>/handover-notes/<int:pk>/edit/", views.NoteEdit.as_view(), name="handover_edit"),
    path("<int:org_id>/handover-notes/<int:pk>/delete/", views.NoteDelete.as_view(), name="handover_delete"),
]
