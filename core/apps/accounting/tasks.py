from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_confirmation(self, payment_id: str) -> dict:
    """
    Send a payment confirmation email to the customer or vendor.
    Retries up to 3 times with a 60-second delay on SMTP failure.
    """
    from apps.accounting.models import Payment

    try:
        payment = Payment.objects.select_related('invoice__order__customer', 'created_by').get(id=payment_id)
    except Payment.DoesNotExist:
        return {'status': 'skipped', 'reason': 'payment not found'}

    # Resolve recipient: customer email (inbound) or created_by email (outbound)
    if payment.payment_type == Payment.PaymentType.INBOUND and payment.invoice:
        customer = payment.invoice.order.customer if hasattr(payment.invoice, 'order') else None
        recipient = customer.email if customer and customer.email else None
    elif payment.created_by and payment.created_by.email:
        recipient = payment.created_by.email
    else:
        recipient = None

    if not recipient:
        return {'status': 'skipped', 'reason': 'no recipient email'}

    direction = 'received' if payment.payment_type == Payment.PaymentType.INBOUND else 'sent'

    try:
        send_mail(
            subject=f'Payment {direction}: {payment.reference}',
            message=(
                f'Dear {recipient},\n\n'
                f'A payment of {payment.amount} has been {direction}.\n'
                f'Reference : {payment.reference}\n'
                f'Date      : {payment.date}\n'
                f'Method    : {payment.get_payment_method_display()}\n\n'
                f'Thank you.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)

    return {'status': 'sent', 'recipient': recipient, 'reference': payment.reference}
