from rest_framework import serializers
from .models import (
    Category, ProductAttribute, ProductAttributeValue,
    Product, ProductVariant, Warehouse, StockMove, StockLevel,
)

_MONEY = dict(max_digits=12, decimal_places=2, read_only=True)


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'parent', 'description', 'created_at', 'children')
        read_only_fields = ('id', 'created_at')

    def get_children(self, obj) -> list:
        return CategorySerializer(obj.children.all(), many=True).data


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.ReadOnlyField(source='attribute.name')

    class Meta:
        model = ProductAttributeValue
        fields = ('id', 'attribute', 'attribute_name', 'value')
        read_only_fields = ('id',)


class ProductAttributeSerializer(serializers.ModelSerializer):
    values = ProductAttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = ProductAttribute
        fields = ('id', 'name', 'values')
        read_only_fields = ('id',)


class StockLevelSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name')

    class Meta:
        model = StockLevel
        fields = ('warehouse', 'warehouse_name', 'quantity', 'updated_at')


class ProductVariantSerializer(serializers.ModelSerializer):
    attribute_values = ProductAttributeValueSerializer(many=True, read_only=True)
    attribute_value_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProductAttributeValue.objects.all(),
        write_only=True,
        source='attribute_values',
    )
    effective_price = serializers.DecimalField(**_MONEY)
    stock_levels = StockLevelSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            'id', 'product', 'sku', 'attribute_values', 'attribute_value_ids',
            'price_override', 'effective_price', 'is_active', 'created_at', 'stock_levels',
        )
        read_only_fields = ('id', 'created_at')


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Product
        fields = ('id', 'name', 'sku', 'category', 'category_name', 'base_price', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    variants = ProductVariantSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    attribute_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProductAttribute.objects.all(),
        write_only=True,
        source='attributes',
    )

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'sku', 'description', 'category', 'category_name',
            'base_price', 'image', 'is_active', 'attributes', 'attribute_ids',
            'variants', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ('id', 'name', 'code', 'address', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class StockMoveSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name')

    class Meta:
        model = StockMove
        fields = (
            'id', 'variant', 'variant_sku', 'warehouse', 'warehouse_name',
            'move_type', 'quantity', 'reference', 'note', 'created_at', 'created_by',
        )
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        move_type = data.get('move_type')
        quantity = data.get('quantity')
        if move_type == StockMove.MoveType.OUT and quantity > 0:
            raise serializers.ValidationError("Stock OUT moves must have a negative quantity.")
        if move_type == StockMove.MoveType.IN and quantity < 0:
            raise serializers.ValidationError("Stock IN moves must have a positive quantity.")
        return data
