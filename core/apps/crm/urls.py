from rest_framework.routers import DefaultRouter
from .views import PipelineViewSet, LeadViewSet, ActivityViewSet

router = DefaultRouter()
router.register('pipeline', PipelineViewSet, basename='pipeline')
router.register('leads', LeadViewSet, basename='lead')
router.register('activities', ActivityViewSet, basename='activity')

urlpatterns = router.urls
