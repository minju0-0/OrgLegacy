from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/archive/", views.ArchiveSearch.as_view(), name="archive_search"),
]
