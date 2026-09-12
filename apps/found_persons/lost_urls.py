from rest_framework.routers import DefaultRouter

from .views import LostPersonViewSet

router = DefaultRouter()
router.register("", LostPersonViewSet, basename="lost-person")

urlpatterns = router.urls
