from django.contrib import admin

from apps.webhooks.models import WebhookDelivery, WebhookEndpoint


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'events_display', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active',)
    readonly_fields = ('id', 'secret', 'created_at')
    search_fields = ('url',)

    def events_display(self, obj):
        return ', '.join(obj.events) if obj.events else 'all'
    events_display.short_description = 'Events'


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ('event', 'endpoint', 'success', 'response_status', 'delivered_at')
    list_filter = ('success', 'event')
    readonly_fields = ('id', 'endpoint', 'event', 'payload', 'response_status', 'success', 'error', 'delivered_at')
    search_fields = ('event', 'endpoint__url')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
