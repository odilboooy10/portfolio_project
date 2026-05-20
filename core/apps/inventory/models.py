import uuid
from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name


class ProductAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)  # e.g. "Color", "Size"

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductAttributeValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)  # e.g. "Red", "XL"

    class Meta:
        unique_together = ('attribute', 'value')
        ordering = ['attribute', 'value']

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products'
    )
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to='inventory/products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    attributes = models.ManyToManyField(ProductAttribute, blank=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    attribute_values = models.ManyToManyField(ProductAttributeValue, blank=True, related_name='variants')
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['product', 'sku']

    def __str__(self):
        values = ', '.join(str(v) for v in self.attribute_values.all())
        return f"{self.product.name} — {values}" if values else self.product.name

    @property
    def effective_price(self):
        return self.price_override if self.price_override is not None else self.product.base_price


class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class StockMove(models.Model):
    """
    Append-only ledger of every inventory movement.
    Positive quantity = stock in; negative = stock out.
    """
    class MoveType(models.TextChoices):
        IN = 'in', 'Stock In'
        OUT = 'out', 'Stock Out'
        ADJUSTMENT = 'adjustment', 'Manual Adjustment'
        TRANSFER = 'transfer', 'Transfer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='stock_moves')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='stock_moves')
    move_type = models.CharField(max_length=20, choices=MoveType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    reference = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='stock_moves'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.move_type} | {self.variant} | {self.quantity} @ {self.warehouse}"

    def clean(self):
        if self.move_type == self.MoveType.OUT and self.quantity > 0:
            raise ValidationError("Stock OUT moves must have a negative quantity.")
        if self.move_type == self.MoveType.IN and self.quantity < 0:
            raise ValidationError("Stock IN moves must have a positive quantity.")


class StockLevel(models.Model):
    """
    Denormalised current stock — updated whenever a StockMove is saved.
    Source of truth is StockMove; this is a fast-read cache.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock_levels')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_levels')
    quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('variant', 'warehouse')

    def __str__(self):
        return f"{self.variant} @ {self.warehouse}: {self.quantity}"
