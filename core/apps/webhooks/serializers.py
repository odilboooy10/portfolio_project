from rest_framework import serializers

from apps.webhooks.models import WebhookDelivery, WebhookEndpoint


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = ('id', 'url', 'events', 'secret', 'is_active', 'created_by', 'created_at')
        read_only_fields = ('id', 'secret', 'created_by', 'created_at')


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ('id', 'endpoint', 'event', 'payload', 'response_status', 'success', 'error', 'delivered_at')
        read_only_fields = ('id', 'endpoint', 'event', 'payload', 'response_status', 'success', 'error', 'delivered_at')
