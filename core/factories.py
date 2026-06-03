import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.utils import timezone


# ── Users ─────────────────────────────────────────────────────────────────────

class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'users.User'

    email = factory.Sequence(lambda n: f'user{n}@erp.local')
    username = factory.Sequence(lambda n: f'user{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'pass123')
    role = 'staff'
    is_active = True


class ManagerUserFactory(UserFactory):
    role = 'staff'
    email = factory.Sequence(lambda n: f'staff{n}@erp.local')
    username = factory.Sequence(lambda n: f'staff{n}')


# ── Inventory ─────────────────────────────────────────────────────────────────

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.Category'

    name = factory.Sequence(lambda n: f'Category {n}')


class ProductAttributeFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.ProductAttribute'

    name = factory.Sequence(lambda n: f'Attribute {n}')


class ProductAttributeValueFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.ProductAttributeValue'

    attribute = factory.SubFactory(ProductAttributeFactory)
    value = factory.Sequence(lambda n: f'Value {n}')


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.Product'

    name = factory.Sequence(lambda n: f'Product {n}')
    sku = factory.Sequence(lambda n: f'SKU-{n:04d}')
    base_price = Decimal('99.99')
    is_active = True


class ProductVariantFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.ProductVariant'

    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f'VAR-{n:04d}')
    is_active = True


class WarehouseFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.Warehouse'

    name = factory.Sequence(lambda n: f'Warehouse {n}')
    code = factory.Sequence(lambda n: f'WH{n:02d}')
    is_active = True


class StockMoveFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.StockMove'

    variant = factory.SubFactory(ProductVariantFactory)
    warehouse = factory.SubFactory(WarehouseFactory)
    move_type = 'in'
    quantity = Decimal('10')


# ── Sales ─────────────────────────────────────────────────────────────────────

class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = 'sales.Customer'

    name = factory.Sequence(lambda n: f'Customer {n}')
    email = factory.Sequence(lambda n: f'customer{n}@example.com')
    is_active = True


class QuotationFactory(DjangoModelFactory):
    class Meta:
        model = 'sales.Quotation'

    customer = factory.SubFactory(CustomerFactory)
    status = 'draft'


class SaleOrderFactory(DjangoModelFactory):
    class Meta:
        model = 'sales.SaleOrder'

    customer = factory.SubFactory(CustomerFactory)
    status = 'confirmed'


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = 'sales.Invoice'

    customer = factory.SubFactory(CustomerFactory)
    status = 'draft'


# ── CRM ───────────────────────────────────────────────────────────────────────

class PipelineFactory(DjangoModelFactory):
    class Meta:
        model = 'crm.Pipeline'

    name = factory.Sequence(lambda n: f'Stage {n}')
    order = factory.Sequence(lambda n: n)
    probability = Decimal('50.00')


class LeadFactory(DjangoModelFactory):
    class Meta:
        model = 'crm.Lead'

    name = factory.Sequence(lambda n: f'Lead {n}')
    contact_name = factory.Faker('name')
    contact_email = factory.Sequence(lambda n: f'lead{n}@example.com')
    pipeline = factory.SubFactory(PipelineFactory)
    priority = 'medium'
    expected_revenue = Decimal('5000.00')
    probability = Decimal('50.00')


class ActivityFactory(DjangoModelFactory):
    class Meta:
        model = 'crm.Activity'

    lead = factory.SubFactory(LeadFactory)
    activity_type = 'call'
    title = factory.Sequence(lambda n: f'Activity {n}')
    is_done = False


# ── Purchase ──────────────────────────────────────────────────────────────────

class VendorFactory(DjangoModelFactory):
    class Meta:
        model = 'purchase.Vendor'

    name = factory.Sequence(lambda n: f'Vendor {n}')
    email = factory.Sequence(lambda n: f'vendor{n}@example.com')
    is_active = True


class PurchaseOrderFactory(DjangoModelFactory):
    class Meta:
        model = 'purchase.PurchaseOrder'

    vendor = factory.SubFactory(VendorFactory)
    status = 'rfq'


# ── Accounting ────────────────────────────────────────────────────────────────

class AccountFactory(DjangoModelFactory):
    class Meta:
        model = 'accounting.Account'

    code = factory.Sequence(lambda n: f'{1000 + n}')
    name = factory.Sequence(lambda n: f'Account {n}')
    account_type = 'asset'
    is_active = True


class JournalFactory(DjangoModelFactory):
    class Meta:
        model = 'accounting.Journal'

    name = factory.Sequence(lambda n: f'Journal {n}')
    code = factory.Sequence(lambda n: f'J{n:02d}')
    journal_type = 'general'
