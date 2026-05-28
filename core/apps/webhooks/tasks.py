import hashlib
import hmac
import json

import requests
from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_webhooks(self, event: str, payload: dict) -> dict:
    """
    POST payload to every active endpoint subscribed to `event`.
    Signs each request with HMAC-SHA256 using the endpoint's secret.
    Retries up to 3 times on connection errors.
    """
    from apps.webhooks.models import WebhookEndpoint, WebhookDelivery

    endpoints = WebhookEndpoint.objects.filter(is_active=True)
    results = []

    for endpoint in endpoints:
        if not endpoint.subscribes_to(event):
            continue

        body = json.dumps({'event': event, 'data': payload}, default=str)
        signature = hmac.new(
            endpoint.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response_status = None
        success = False
        error = ''

        try:
            resp = requests.post(
                endpoint.url,
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-ERP-Event': event,
                    'X-ERP-Signature': f'sha256={signature}',
                },
                timeout=10,
            )
            response_status = resp.status_code
            success = 200 <= resp.status_code < 300
        except requests.RequestException as exc:
            error = str(exc)

        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event=event,
            payload={'event': event, 'data': payload},
            response_status=response_status,
            success=success,
            error=error,
        )
        results.append({'url': endpoint.url, 'success': success, 'status': response_status})

    return {'event': event, 'dispatched': len(results), 'results': results}
