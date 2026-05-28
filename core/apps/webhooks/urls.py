from rest_framework.routers import DefaultRouter

from apps.webhooks.views import WebhookDeliveryViewSet, WebhookEndpointViewSet

router = DefaultRouter()
router.register('endpoints', WebhookEndpointViewSet, basename='webhook-endpoint')
router.register('deliveries', WebhookDeliveryViewSet, basename='webhook-delivery')

urlpatterns = router.urls
