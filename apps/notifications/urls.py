from django.urls import path

from . import views

urlpatterns = [
    path("read-all/", views.read_all_view, name="notifications_read_all"),
    path("<int:pk>/go/", views.go_view, name="notifications_go"),
]
