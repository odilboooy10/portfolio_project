from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsAdmin
from apps.webhooks.models import WebhookDelivery, WebhookEndpoint
from apps.webhooks.serializers import WebhookDeliverySerializer, WebhookEndpointSerializer


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class WebhookDeliveryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = WebhookDelivery.objects.select_related('endpoint').all()
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
