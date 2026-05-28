import uuid
import secrets
from django.db import models


class WebhookEndpoint(models.Model):
    """A registered URL that receives event payloads."""

    EVENTS = [
        ('order.confirmed',  'Sale Order Confirmed'),
        ('invoice.paid',     'Invoice Paid'),
        ('payment.created',  'Payment Created'),
        ('lead.won',         'CRM Lead Won'),
        ('po.received',      'Purchase Order Received'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url        = models.URLField(max_length=500)
    events     = models.JSONField(
        default=list,
        help_text='List of event names this endpoint subscribes to. Empty = all events.',
    )
    secret     = models.CharField(
        max_length=64, editable=False,
        help_text='HMAC-SHA256 signing secret. Sent as X-ERP-Signature header.',
    )
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='webhook_endpoints',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.url} ({', '.join(self.events) or 'all'})"

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def subscribes_to(self, event: str) -> bool:
        return not self.events or event in self.events


class WebhookDelivery(models.Model):
    """Log of every delivery attempt for an endpoint."""

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint        = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries',
    )
    event           = models.CharField(max_length=50)
    payload         = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    success         = models.BooleanField(default=False)
    error           = models.TextField(blank=True)
    delivered_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivered_at']

    def __str__(self):
        status = 'OK' if self.success else f'FAIL {self.response_status or "no-response"}'
        return f"{self.event} → {self.endpoint.url} [{status}]"
