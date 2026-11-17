from django.urls import path

from . import views


urlpatterns = [
    path("", views.profile_view, name="profile"),
    path("avatar/", views.avatar_save_view, name="profile_avatar_save"),
    path("avatar/remove/", views.avatar_remove_view, name="profile_avatar_remove"),
]
