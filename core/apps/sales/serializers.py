from rest_framework import serializers
from .models import Customer, Quotation, QuotationLine, SaleOrder, SaleOrderLine, Invoice, InvoiceLine


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            'id', 'name', 'email', 'phone', 'address',
            'company', 'tax_id', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


# ── Quotation ─────────────────────────────────────────────────────────────────

class QuotationLineSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    product_name = serializers.ReadOnlyField(source='variant.product.name')

    class Meta:
        model = QuotationLine
        fields = (
            'id', 'variant', 'variant_sku', 'product_name',
            'quantity', 'unit_price', 'description', 'line_total',
        )
        read_only_fields = ('id',)


class QuotationListSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    total = serializers.ReadOnlyField()

    class Meta:
        model = Quotation
        fields = (
            'id', 'reference', 'customer', 'customer_name',
            'status', 'validity_date', 'discount', 'total', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'created_at')


class QuotationDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    lines = QuotationLineSerializer(many=True)
    subtotal = serializers.ReadOnlyField()
    total = serializers.ReadOnlyField()
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Quotation
        fields = (
            'id', 'reference', 'customer', 'customer_name', 'status',
            'validity_date', 'note', 'discount', 'subtotal', 'total',
            'lines', 'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'reference', 'status', 'created_at', 'updated_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        quotation = Quotation.objects.create(**validated_data)
        for line in lines_data:
            QuotationLine.objects.create(quotation=quotation, **line)
        return quotation

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                QuotationLine.objects.create(quotation=instance, **line)
        return instance


# ── Sale Order ────────────────────────────────────────────────────────────────

class SaleOrderLineSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    product_name = serializers.ReadOnlyField(source='variant.product.name')

    class Meta:
        model = SaleOrderLine
        fields = (
            'id', 'variant', 'variant_sku', 'product_name',
            'quantity', 'unit_price', 'description', 'line_total',
        )
        read_only_fields = ('id',)


class SaleOrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    total = serializers.ReadOnlyField()

    class Meta:
        model = SaleOrder
        fields = (
            'id', 'reference', 'customer', 'customer_name',
            'status', 'discount', 'total', 'confirmed_at',
        )
        read_only_fields = ('id', 'reference', 'confirmed_at')


class SaleOrderDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    lines = SaleOrderLineSerializer(many=True)
    subtotal = serializers.ReadOnlyField()
    total = serializers.ReadOnlyField()
    confirmed_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = SaleOrder
        fields = (
            'id', 'reference', 'quotation', 'customer', 'customer_name', 'status',
            'note', 'discount', 'subtotal', 'total',
            'lines', 'confirmed_by', 'confirmed_at', 'updated_at',
        )
        read_only_fields = ('id', 'reference', 'confirmed_at', 'updated_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        order = SaleOrder.objects.create(**validated_data)
        for line in lines_data:
            SaleOrderLine.objects.create(order=order, **line)
        return order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                SaleOrderLine.objects.create(order=instance, **line)
        return instance


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceLineSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    product_name = serializers.ReadOnlyField(source='variant.product.name')

    class Meta:
        model = InvoiceLine
        fields = (
            'id', 'variant', 'variant_sku', 'product_name',
            'quantity', 'unit_price', 'description', 'line_total',
        )
        read_only_fields = ('id',)


class InvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    total = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = (
            'id', 'reference', 'customer', 'customer_name',
            'status', 'issue_date', 'due_date', 'discount', 'total', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'created_at')


class InvoiceDetailSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    lines = InvoiceLineSerializer(many=True)
    subtotal = serializers.ReadOnlyField()
    total = serializers.ReadOnlyField()
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Invoice
        fields = (
            'id', 'reference', 'sale_order', 'customer', 'customer_name', 'status',
            'issue_date', 'due_date', 'note', 'discount', 'subtotal', 'total',
            'paid_at', 'lines', 'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'reference', 'status', 'paid_at', 'created_at', 'updated_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        invoice = Invoice.objects.create(**validated_data)
        for line in lines_data:
            InvoiceLine.objects.create(invoice=invoice, **line)
        return invoice

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                InvoiceLine.objects.create(invoice=instance, **line)
        return instance
