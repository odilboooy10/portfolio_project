from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invoice_pdf_email(self, invoice_id: str) -> dict:
    """
    Render invoice as PDF and email it to the customer.
    Triggered after an invoice is marked as issued.
    """
    from apps.sales.models import Invoice
    import weasyprint

    try:
        invoice = Invoice.objects.select_related(
            'customer', 'sale_order'
        ).prefetch_related('lines__variant__product').get(id=invoice_id)
    except Invoice.DoesNotExist:
        return {'status': 'skipped', 'reason': 'invoice not found'}

    recipient = invoice.customer.email
    if not recipient:
        return {'status': 'skipped', 'reason': 'customer has no email'}

    try:
        html = render_to_string('pdf/invoice.html', {'invoice': invoice})
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()

        email = EmailMessage(
            subject=f'Invoice {invoice.reference} from ERP Core',
            body=(
                f'Dear {invoice.customer.name},\n\n'
                f'Please find your invoice {invoice.reference} attached.\n\n'
                f'Amount due: ${invoice.total}\n'
                f'Due date  : {invoice.due_date or "upon receipt"}\n\n'
                f'Thank you for your business.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.attach(f'{invoice.reference}.pdf', pdf_bytes, 'application/pdf')
        email.send(fail_silently=False)

    except Exception as exc:
        raise self.retry(exc=exc)

    return {'status': 'sent', 'recipient': recipient, 'reference': invoice.reference}
