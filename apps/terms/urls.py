from django.urls import path

from . import views

urlpatterns = [
    path("<int:org_id>/next-year/", views.PlanPage.as_view(), name="term_plan"),
    path("<int:org_id>/next-year/save/", views.PlanSave.as_view(), name="term_plan_save"),
    path("<int:org_id>/next-year/clear/", views.PlanClear.as_view(), name="term_plan_clear"),
]
