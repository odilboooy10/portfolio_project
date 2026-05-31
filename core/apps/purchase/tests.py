import pytest
from decimal import Decimal
from factories import VendorFactory, PurchaseOrderFactory, ProductVariantFactory, WarehouseFactory
from apps.purchase.models import PurchaseOrder, Receipt
from apps.inventory.models import StockLevel


@pytest.mark.django_db
class TestVendorAPI:
    def test_create_vendor(self, auth_client):
        response = auth_client.post('/api/v1/purchase/vendors/', {
            'name': 'ACME Supplies',
            'email': 'supply@acme.com',
        })
        assert response.status_code == 201
        assert response.data['name'] == 'ACME Supplies'

    def test_list_vendors(self, auth_client):
        VendorFactory.create_batch(3)
        response = auth_client.get('/api/v1/purchase/vendors/')
        assert response.status_code == 200
        assert len(response.data['results']) == 3


@pytest.mark.django_db
class TestPurchaseOrderFlow:
    def _create_po_with_line(self, auth_client):
        vendor = VendorFactory()
        variant = ProductVariantFactory()
        response = auth_client.post('/api/v1/purchase/orders/', {
            'vendor': str(vendor.id),
            'lines': [
                {'variant': str(variant.id), 'quantity': '10', 'unit_price': '25.00'}
            ],
        }, format='json')
        assert response.status_code == 201
        return response.data['id'], variant

    def test_create_rfq(self, auth_client):
        po_id, _ = self._create_po_with_line(auth_client)
        po = PurchaseOrder.objects.get(id=po_id)
        assert po.status == 'rfq'
        assert po.reference.startswith('PO-')

    def test_confirm_rfq(self, auth_client):
        po_id, _ = self._create_po_with_line(auth_client)
        response = auth_client.post(f'/api/v1/purchase/orders/{po_id}/confirm/')
        assert response.status_code == 200
        assert response.data['status'] == 'confirmed'

    def test_cannot_confirm_empty_rfq(self, auth_client):
        vendor = VendorFactory()
        response = auth_client.post('/api/v1/purchase/orders/', {
            'vendor': str(vendor.id),
            'lines': [],
        }, format='json')
        po_id = response.data['id']
        response = auth_client.post(f'/api/v1/purchase/orders/{po_id}/confirm/')
        assert response.status_code == 400

    def test_receive_goods_creates_receipt_and_updates_stock(self, auth_client):
        po_id, variant = self._create_po_with_line(auth_client)
        auth_client.post(f'/api/v1/purchase/orders/{po_id}/confirm/')
        warehouse = WarehouseFactory()
        po = PurchaseOrder.objects.get(id=po_id)
        po_line = po.lines.first()

        response = auth_client.post(f'/api/v1/purchase/orders/{po_id}/receive/', {
            'warehouse': str(warehouse.id),
            'lines': [
                {'purchase_order_line': str(po_line.id), 'quantity_received': '10'}
            ],
        }, format='json')
        assert response.status_code == 201
        assert response.data['reference'].startswith('REC-')
        assert Receipt.objects.filter(purchase_order_id=po_id).exists()

        level = StockLevel.objects.get(variant=variant, warehouse=warehouse)
        assert level.quantity == Decimal('10')

        po.refresh_from_db()
        assert po.status == 'received'

    def test_partial_receive_keeps_confirmed_status(self, auth_client):
        po_id, variant = self._create_po_with_line(auth_client)
        auth_client.post(f'/api/v1/purchase/orders/{po_id}/confirm/')
        warehouse = WarehouseFactory()
        po = PurchaseOrder.objects.get(id=po_id)
        po_line = po.lines.first()

        auth_client.post(f'/api/v1/purchase/orders/{po_id}/receive/', {
            'warehouse': str(warehouse.id),
            'lines': [
                {'purchase_order_line': str(po_line.id), 'quantity_received': '5'}
            ],
        }, format='json')

        po.refresh_from_db()
        assert po.status == 'confirmed'

    def test_bill_received_order(self, auth_client):
        po_id, variant = self._create_po_with_line(auth_client)
        auth_client.post(f'/api/v1/purchase/orders/{po_id}/confirm/')
        warehouse = WarehouseFactory()
        po = PurchaseOrder.objects.get(id=po_id)
        po_line = po.lines.first()
        auth_client.post(f'/api/v1/purchase/orders/{po_id}/receive/', {
            'warehouse': str(warehouse.id),
            'lines': [{'purchase_order_line': str(po_line.id), 'quantity_received': '10'}],
        }, format='json')

        response = auth_client.post(f'/api/v1/purchase/orders/{po_id}/bill/')
        assert response.status_code == 200
        assert response.data['status'] == 'billed'

    def test_receipts_are_read_only(self, auth_client):
        response = auth_client.post('/api/v1/purchase/receipts/', {})
        assert response.status_code == 405
