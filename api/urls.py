from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import missions_par_direction

router = DefaultRouter()
# router.register("agents", AgentViewSet)
# router.register("missions", MissionViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("missions/par-direction/", missions_par_direction),
]
