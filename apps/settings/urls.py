from django.urls import path
from . import views

urlpatterns = [
    path('', views.settings_view, name='settings'),
    path('notifications/', views.save_notifications_view, name='settings_save_notifications'),
    path('export/', views.export_request_view, name='settings_export'),
    path('export/download/', views.export_download_view, name='settings_export_download'),
]
