from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("styleguide/", views.styleguide_view, name="styleguide"),
]