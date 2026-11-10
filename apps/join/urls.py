from django.urls import path

from . import views

urlpatterns = [
    path("preview/", views.preview_view, name="join_preview"),
    path("redeem/", views.redeem_view, name="join_redeem"),
]
