"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='login:login', permanent=False)),
    path('login/', include('apps.login.urls')),
    path('register/', include('apps.register.urls')),
    path('home/', include('apps.home.urls')),
    path('profile/', include('apps.profile.urls')),
    path('settings/', include('apps.settings.urls')),
]
