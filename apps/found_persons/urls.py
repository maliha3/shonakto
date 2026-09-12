from rest_framework.routers import DefaultRouter

from .views import FoundPersonViewSet

router = DefaultRouter()
router.register("", FoundPersonViewSet, basename="found-person")

urlpatterns = router.urls
