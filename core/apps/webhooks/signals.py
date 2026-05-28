from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

_lead_won_at: dict = {}


@receiver(post_save, sender='sales.SaleOrder')
def on_order_confirmed(sender, instance, created, **kwargs):
    if not created and instance.status == 'confirmed':
        from apps.webhooks.tasks import dispatch_webhooks
        dispatch_webhooks.delay('order.confirmed', {
            'id': str(instance.id),
            'reference': instance.reference,
            'customer': instance.customer.name,
            'status': instance.status,
        })


@receiver(post_save, sender='sales.Invoice')
def on_invoice_paid(sender, instance, created, **kwargs):
    if not created and instance.status == 'paid':
        from apps.webhooks.tasks import dispatch_webhooks
        dispatch_webhooks.delay('invoice.paid', {
            'id': str(instance.id),
            'reference': instance.reference,
            'customer': instance.customer.name,
            'total': str(instance.total),
            'paid_at': str(instance.paid_at),
        })


@receiver(post_save, sender='accounting.Payment')
def on_payment_created(sender, instance, created, **kwargs):
    if created:
        from apps.webhooks.tasks import dispatch_webhooks
        dispatch_webhooks.delay('payment.created', {
            'id': str(instance.id),
            'reference': instance.reference,
            'payment_type': instance.payment_type,
            'amount': str(instance.amount),
            'date': str(instance.date),
        })


@receiver(pre_save, sender='crm.Lead')
def _snapshot_lead_won_at(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.filter(pk=instance.pk).values_list('won_at', flat=True).first()
            _lead_won_at[str(instance.pk)] = old
        except Exception:
            pass


@receiver(post_save, sender='crm.Lead')
def on_lead_won(sender, instance, created, **kwargs):
    if created or not instance.won_at:
        _lead_won_at.pop(str(instance.pk), None)
        return
    old_won_at = _lead_won_at.pop(str(instance.pk), ...)
    if old_won_at is None:
        from apps.webhooks.tasks import dispatch_webhooks
        dispatch_webhooks.delay('lead.won', {
            'id': str(instance.id),
            'name': instance.name,
            'contact_email': instance.contact_email,
            'expected_revenue': str(instance.expected_revenue),
        })


@receiver(post_save, sender='purchase.PurchaseOrder')
def on_po_received(sender, instance, created, **kwargs):
    if not created and instance.status == 'received':
        from apps.webhooks.tasks import dispatch_webhooks
        dispatch_webhooks.delay('po.received', {
            'id': str(instance.id),
            'reference': instance.reference,
            'vendor': instance.vendor.name,
            'status': instance.status,
        })
