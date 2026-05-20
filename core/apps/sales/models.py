import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent to Customer'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotations')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    validity_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='quotations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.customer}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = Quotation.objects.order_by('-created_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"QUO-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(line.line_total for line in self.lines.all())

    @property
    def total(self):
        return self.subtotal * (1 - self.discount / 100)


class QuotationLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='lines')
    variant = models.ForeignKey(
        'inventory.ProductVariant', on_delete=models.PROTECT, related_name='quotation_lines'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quotation.reference} / {self.variant.sku} x {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class SaleOrder(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    quotation = models.OneToOneField(
        Quotation, null=True, blank=True, on_delete=models.SET_NULL, related_name='sale_order'
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sale_orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    note = models.TextField(blank=True)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    confirmed_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_orders'
    )
    confirmed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-confirmed_at']

    def __str__(self):
        return f"{self.reference} — {self.customer}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = SaleOrder.objects.order_by('-confirmed_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"SO-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(line.line_total for line in self.lines.all())

    @property
    def total(self):
        return self.subtotal * (1 - self.discount / 100)


class SaleOrderLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='lines')
    variant = models.ForeignKey(
        'inventory.ProductVariant', on_delete=models.PROTECT, related_name='sale_order_lines'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.order.reference} / {self.variant.sku} x {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    sale_order = models.ForeignKey(
        SaleOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices'
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.customer}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = Invoice.objects.order_by('-created_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"INV-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(line.line_total for line in self.lines.all())

    @property
    def total(self):
        return self.subtotal * (1 - self.discount / 100)


class InvoiceLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    variant = models.ForeignKey(
        'inventory.ProductVariant', on_delete=models.PROTECT, related_name='invoice_lines'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.invoice.reference} / {self.variant.sku} x {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price
