import pytest
from decimal import Decimal
from factories import (
    ProductFactory, ProductVariantFactory, WarehouseFactory,
    CategoryFactory,
)
from apps.inventory.models import StockMove, StockLevel


@pytest.mark.django_db
class TestProductModel:
    def test_product_str(self):
        product = ProductFactory(name='T-Shirt', sku='TSH-001')
        assert 'T-Shirt' in str(product)
        assert 'TSH-001' in str(product)

    def test_variant_effective_price_uses_override(self):
        product = ProductFactory(base_price=Decimal('100.00'))
        variant = ProductVariantFactory(product=product, price_override=Decimal('80.00'))
        assert variant.effective_price == Decimal('80.00')

    def test_variant_effective_price_falls_back_to_base(self):
        product = ProductFactory(base_price=Decimal('100.00'))
        variant = ProductVariantFactory(product=product, price_override=None)
        assert variant.effective_price == Decimal('100.00')

    def test_category_str_with_parent(self):
        parent = CategoryFactory(name='Clothing')
        child = CategoryFactory(name='T-Shirts', parent=parent)
        assert str(child) == 'Clothing / T-Shirts'


@pytest.mark.django_db
class TestStockMoveAPI:
    def test_stock_in_increases_level(self, auth_client):
        variant = ProductVariantFactory()
        warehouse = WarehouseFactory()

        response = auth_client.post('/api/v1/inventory/stock/moves/', {
            'variant': str(variant.id),
            'warehouse': str(warehouse.id),
            'move_type': 'in',
            'quantity': '10',
        })
        assert response.status_code == 201
        level = StockLevel.objects.get(variant=variant, warehouse=warehouse)
        assert level.quantity == Decimal('10')

    def test_stock_out_decreases_level(self, auth_client):
        variant = ProductVariantFactory()
        warehouse = WarehouseFactory()
        StockLevel.objects.create(variant=variant, warehouse=warehouse, quantity=Decimal('20'))

        response = auth_client.post('/api/v1/inventory/stock/moves/', {
            'variant': str(variant.id),
            'warehouse': str(warehouse.id),
            'move_type': 'out',
            'quantity': '-5',
        })
        assert response.status_code == 201
        level = StockLevel.objects.get(variant=variant, warehouse=warehouse)
        assert level.quantity == Decimal('15')

    def test_stock_move_is_append_only(self, auth_client):
        variant = ProductVariantFactory()
        warehouse = WarehouseFactory()
        auth_client.post('/api/v1/inventory/stock/moves/', {
            'variant': str(variant.id),
            'warehouse': str(warehouse.id),
            'move_type': 'in',
            'quantity': '10',
        })
        move = StockMove.objects.first()
        response = auth_client.put(f'/api/v1/inventory/stock/moves/{move.id}/', {})
        assert response.status_code == 405

    def test_manual_adjustment(self, auth_client):
        variant = ProductVariantFactory()
        warehouse = WarehouseFactory()
        StockLevel.objects.create(variant=variant, warehouse=warehouse, quantity=Decimal('10'))

        response = auth_client.post('/api/v1/inventory/stock/moves/adjust/', {
            'variant': str(variant.id),
            'warehouse': str(warehouse.id),
            'quantity': '25',
        })
        assert response.status_code == 201
        level = StockLevel.objects.get(variant=variant, warehouse=warehouse)
        assert level.quantity == Decimal('25')


@pytest.mark.django_db
class TestProductAPI:
    def test_list_products(self, auth_client):
        ProductFactory.create_batch(3)
        response = auth_client.get('/api/v1/inventory/products/')
        assert response.status_code == 200
        assert len(response.data['results']) == 3

    def test_create_product(self, auth_client):
        response = auth_client.post('/api/v1/inventory/products/', {
            'name': 'New Product',
            'sku': 'NEW-001',
            'base_price': '49.99',
        })
        assert response.status_code == 201
        assert response.data['sku'] == 'NEW-001'

    def test_unauthenticated_cannot_list(self, api_client):
        response = api_client.get('/api/v1/inventory/products/')
        assert response.status_code == 401
