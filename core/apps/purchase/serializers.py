from rest_framework import serializers
from .models import Vendor, PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine

_MONEY = dict(max_digits=12, decimal_places=2, read_only=True)


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = (
            'id', 'name', 'email', 'phone', 'address',
            'company', 'tax_id', 'payment_terms', 'is_active',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(**_MONEY)
    remaining_qty = serializers.DecimalField(**_MONEY)
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    product_name = serializers.ReadOnlyField(source='variant.product.name')

    class Meta:
        model = PurchaseOrderLine
        fields = (
            'id', 'variant', 'variant_sku', 'product_name',
            'quantity', 'unit_price', 'description',
            'received_qty', 'remaining_qty', 'line_total',
        )
        read_only_fields = ('id', 'received_qty')


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.name')
    total = serializers.DecimalField(**_MONEY)

    class Meta:
        model = PurchaseOrder
        fields = (
            'id', 'reference', 'vendor', 'vendor_name',
            'status', 'expected_delivery', 'discount', 'total', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'created_at')


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.name')
    lines = PurchaseOrderLineSerializer(many=True)
    subtotal = serializers.DecimalField(**_MONEY)
    total = serializers.DecimalField(**_MONEY)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = PurchaseOrder
        fields = (
            'id', 'reference', 'vendor', 'vendor_name', 'status',
            'expected_delivery', 'note', 'discount', 'subtotal', 'total',
            'lines', 'created_by', 'confirmed_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'reference', 'status', 'confirmed_at', 'created_at', 'updated_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        order = PurchaseOrder.objects.create(**validated_data)
        for line in lines_data:
            PurchaseOrderLine.objects.create(order=order, **line)
        return order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                PurchaseOrderLine.objects.create(order=instance, **line)
        return instance


class ReceiptLineSerializer(serializers.ModelSerializer):
    variant_sku = serializers.ReadOnlyField(source='purchase_order_line.variant.sku')
    product_name = serializers.ReadOnlyField(source='purchase_order_line.variant.product.name')

    class Meta:
        model = ReceiptLine
        fields = (
            'id', 'purchase_order_line', 'variant_sku', 'product_name', 'quantity_received',
        )
        read_only_fields = ('id',)


class ReceiptSerializer(serializers.ModelSerializer):
    lines = ReceiptLineSerializer(many=True)
    received_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    purchase_order_reference = serializers.ReadOnlyField(source='purchase_order.reference')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name')

    class Meta:
        model = Receipt
        fields = (
            'id', 'reference', 'purchase_order', 'purchase_order_reference',
            'warehouse', 'warehouse_name', 'note',
            'lines', 'received_by', 'received_at',
        )
        read_only_fields = ('id', 'reference', 'received_at')

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        receipt = Receipt.objects.create(**validated_data)
        for line in lines_data:
            ReceiptLine.objects.create(receipt=receipt, **line)
        return receipt
