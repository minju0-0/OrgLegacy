from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/suppliers/<int:pk>/rate/", views.RateSupplier.as_view(), name="rating_submit"),
]
