from django.urls import include, path
from rest_framework import routers

from .views import (AssignmentsCreateView, AssignmentsViewSet, PlanCreateView,
                    ProjectViewSet, ResourceViewSet, SkillViewSet, TaskViewSet)

router = routers.DefaultRouter()
router.register("projects", ProjectViewSet)
router.register("tasks", TaskViewSet)
router.register("resources", ResourceViewSet)
router.register("skill", SkillViewSet)
router.register("assignment", AssignmentsViewSet)


urlpatterns = [
    path("api/", include(router.urls)),
    path("api/plan/", PlanCreateView.as_view(), name="plan-create"),
    path("api/assign/", AssignmentsCreateView.as_view(), name="assign"),
]
