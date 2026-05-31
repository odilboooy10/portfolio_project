import pytest
from decimal import Decimal
from factories import CustomerFactory, QuotationFactory, ProductVariantFactory
from apps.sales.models import Quotation, SaleOrder, Invoice


@pytest.mark.django_db
class TestCustomerAPI:
    def test_create_customer(self, auth_client):
        response = auth_client.post('/api/v1/sales/customers/', {
            'name': 'Acme Corp',
            'email': 'acme@example.com',
        })
        assert response.status_code == 201
        assert response.data['name'] == 'Acme Corp'

    def test_list_customers(self, auth_client):
        CustomerFactory.create_batch(3)
        response = auth_client.get('/api/v1/sales/customers/')
        assert response.status_code == 200
        assert len(response.data['results']) == 3


@pytest.mark.django_db
class TestQuotationFlow:
    def _create_quotation_with_line(self, auth_client):
        customer = CustomerFactory()
        variant = ProductVariantFactory()
        response = auth_client.post('/api/v1/sales/quotations/', {
            'customer': str(customer.id),
            'lines': [
                {
                    'variant': str(variant.id),
                    'quantity': '2',
                    'unit_price': '50.00',
                }
            ],
        }, format='json')
        assert response.status_code == 201
        return response.data['id']

    def test_create_quotation(self, auth_client):
        quotation_id = self._create_quotation_with_line(auth_client)
        quotation = Quotation.objects.get(id=quotation_id)
        assert quotation.status == 'draft'
        assert quotation.reference.startswith('QUO-')

    def test_send_quotation(self, auth_client):
        quotation_id = self._create_quotation_with_line(auth_client)
        response = auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/send/')
        assert response.status_code == 200
        assert response.data['status'] == 'sent'

    def test_confirm_quotation_creates_sale_order(self, auth_client):
        quotation_id = self._create_quotation_with_line(auth_client)
        response = auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/confirm/')
        assert response.status_code == 201
        assert response.data['reference'].startswith('SO-')
        assert SaleOrder.objects.filter(quotation_id=quotation_id).exists()
        assert Quotation.objects.get(id=quotation_id).status == 'confirmed'

    def test_cannot_confirm_empty_quotation(self, auth_client):
        customer = CustomerFactory()
        response = auth_client.post('/api/v1/sales/quotations/', {
            'customer': str(customer.id),
            'lines': [],
        }, format='json')
        quotation_id = response.data['id']
        response = auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/confirm/')
        assert response.status_code == 400

    def test_cancel_quotation(self, auth_client):
        quotation_id = self._create_quotation_with_line(auth_client)
        response = auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/cancel/')
        assert response.status_code == 200
        assert response.data['status'] == 'cancelled'

    def test_cannot_cancel_confirmed_quotation(self, auth_client):
        quotation_id = self._create_quotation_with_line(auth_client)
        auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/confirm/')
        response = auth_client.post(f'/api/v1/sales/quotations/{quotation_id}/cancel/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestSaleOrderFlow:
    def _confirmed_order(self, auth_client):
        customer = CustomerFactory()
        variant = ProductVariantFactory()
        q = auth_client.post('/api/v1/sales/quotations/', {
            'customer': str(customer.id),
            'lines': [{'variant': str(variant.id), 'quantity': '1', 'unit_price': '100.00'}],
        }, format='json')
        auth_client.post(f'/api/v1/sales/quotations/{q.data["id"]}/confirm/')
        return SaleOrder.objects.get(quotation_id=q.data['id'])

    def test_create_invoice_from_order(self, auth_client):
        order = self._confirmed_order(auth_client)
        response = auth_client.post(f'/api/v1/sales/orders/{order.id}/invoice/')
        assert response.status_code == 201
        assert response.data['reference'].startswith('INV-')
        assert Invoice.objects.filter(sale_order=order).exists()

    def test_full_flow_quotation_to_paid(self, auth_client):
        order = self._confirmed_order(auth_client)
        inv_resp = auth_client.post(f'/api/v1/sales/orders/{order.id}/invoice/')
        inv_id = inv_resp.data['id']
        auth_client.post(f'/api/v1/sales/invoices/{inv_id}/issue/')
        paid_resp = auth_client.post(f'/api/v1/sales/invoices/{inv_id}/mark_paid/')
        assert paid_resp.status_code == 200
        assert paid_resp.data['status'] == 'paid'
        order.refresh_from_db()
        assert order.status == 'done'

    def test_subtotal_and_total_calculation(self, auth_client):
        customer = CustomerFactory()
        variant = ProductVariantFactory()
        q = auth_client.post('/api/v1/sales/quotations/', {
            'customer': str(customer.id),
            'discount': '10.00',
            'lines': [{'variant': str(variant.id), 'quantity': '2', 'unit_price': '100.00'}],
        }, format='json')
        quotation = Quotation.objects.get(id=q.data['id'])
        assert quotation.subtotal == Decimal('200.00')
        assert quotation.total == Decimal('180.00')  # 10% discount
