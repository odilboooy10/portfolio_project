import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.audit.mixins import AuditableMixin


class Vendor(AuditableMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(AuditableMixin, models.Model):
    class Status(models.TextChoices):
        RFQ = 'rfq', 'Request for Quotation'
        CONFIRMED = 'confirmed', 'Purchase Order'
        RECEIVED = 'received', 'Received'
        BILLED = 'billed', 'Billed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RFQ)
    expected_delivery = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='purchase_orders'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.vendor}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = PurchaseOrder.objects.order_by('-created_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"PO-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(line.line_total for line in self.lines.all())

    @property
    def total(self):
        return self.subtotal * (1 - self.discount / 100)


class PurchaseOrderLine(AuditableMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    variant = models.ForeignKey(
        'inventory.ProductVariant', on_delete=models.PROTECT, related_name='purchase_order_lines'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)
    received_qty = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.order.reference} / {self.variant.sku} x {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def remaining_qty(self):
        return self.quantity - self.received_qty


class Receipt(AuditableMixin, models.Model):
    """Records goods received against a Purchase Order."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name='receipts'
    )
    warehouse = models.ForeignKey(
        'inventory.Warehouse', on_delete=models.PROTECT, related_name='receipts'
    )
    note = models.TextField(blank=True)
    received_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='receipts'
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.reference} ← {self.purchase_order.reference}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = Receipt.objects.order_by('-received_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"REC-{next_num:05d}"
        super().save(*args, **kwargs)


class ReceiptLine(AuditableMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='lines')
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine, on_delete=models.PROTECT, related_name='receipt_lines'
    )
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.receipt.reference} / {self.purchase_order_line.variant.sku} x {self.quantity_received}"
