from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F

from apps.users.permissions import InventoryPermission
from .models import (
    Category, ProductAttribute, ProductAttributeValue,
    Product, ProductVariant, Warehouse, StockMove, StockLevel,
)
from .serializers import (
    CategorySerializer, ProductAttributeSerializer, ProductAttributeValueSerializer,
    ProductListSerializer, ProductDetailSerializer,
    ProductVariantSerializer, WarehouseSerializer, StockMoveSerializer, StockLevelSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related('parent').prefetch_related('children')
    serializer_class = CategorySerializer
    permission_classes = [InventoryPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('root_only'):
            qs = qs.filter(parent__isnull=True)
        return qs


class ProductAttributeViewSet(viewsets.ModelViewSet):
    queryset = ProductAttribute.objects.prefetch_related('values')
    serializer_class = ProductAttributeSerializer
    permission_classes = [InventoryPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ProductAttributeValueViewSet(viewsets.ModelViewSet):
    queryset = ProductAttributeValue.objects.select_related('attribute')
    serializer_class = ProductAttributeValueSerializer
    permission_classes = [InventoryPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        attribute_id = self.request.query_params.get('attribute')
        if attribute_id:
            qs = qs.filter(attribute_id=attribute_id)
        return qs


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    permission_classes = [InventoryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'base_price', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        qs = Product.objects.select_related('category').prefetch_related('attributes', 'variants')
        if not self.request.user.is_manager:
            qs = qs.filter(is_active=True)
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.select_related('product').prefetch_related('attribute_values', 'stock_levels__warehouse')
    serializer_class = ProductVariantSerializer
    permission_classes = [InventoryPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [InventoryPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']


class StockMoveViewSet(viewsets.ModelViewSet):
    queryset = StockMove.objects.select_related('variant__product', 'warehouse', 'created_by')
    serializer_class = StockMoveSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']  # ledger is append-only

    def get_queryset(self):
        qs = super().get_queryset()
        variant_id = self.request.query_params.get('variant')
        warehouse_id = self.request.query_params.get('warehouse')
        if variant_id:
            qs = qs.filter(variant_id=variant_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        move = serializer.save()
        # Update or create the StockLevel cache
        stock_level, _ = StockLevel.objects.get_or_create(
            variant=move.variant,
            warehouse=move.warehouse,
            defaults={'quantity': 0},
        )
        StockLevel.objects.filter(pk=stock_level.pk).update(
            quantity=F('quantity') + move.quantity
        )

    @action(detail=False, methods=['post'], url_path='adjust', permission_classes=[InventoryPermission])
    @transaction.atomic
    def adjust(self, request):
        """
        Manual stock adjustment endpoint.
        Accepts: variant, warehouse, quantity (absolute target), note.
        Creates a corrective StockMove so the ledger stays intact.
        """
        variant_id = request.data.get('variant')
        warehouse_id = request.data.get('warehouse')
        target_qty = request.data.get('quantity')
        note = request.data.get('note', '')

        if variant_id is None or warehouse_id is None or target_qty is None:
            return Response(
                {'detail': 'variant, warehouse, and quantity are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from decimal import Decimal
            target_qty = Decimal(str(target_qty))
        except Exception:
            return Response({'detail': 'quantity must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

        stock_level, _ = StockLevel.objects.get_or_create(
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            defaults={'quantity': 0},
        )
        delta = target_qty - stock_level.quantity

        move = StockMove.objects.create(
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            move_type=StockMove.MoveType.ADJUSTMENT,
            quantity=delta,
            note=note,
            reference='manual-adjustment',
            created_by=request.user,
        )
        StockLevel.objects.filter(pk=stock_level.pk).update(quantity=target_qty)

        return Response(StockMoveSerializer(move, context={'request': request}).data, status=status.HTTP_201_CREATED)


class StockLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockLevel.objects.select_related('variant__product', 'warehouse')
    serializer_class = StockLevelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        variant_id = self.request.query_params.get('variant')
        warehouse_id = self.request.query_params.get('warehouse')
        low_stock = self.request.query_params.get('low_stock')
        if variant_id:
            qs = qs.filter(variant_id=variant_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if low_stock:
            try:
                threshold = float(low_stock)
                qs = qs.filter(quantity__lte=threshold)
            except ValueError:
                pass
        return qs
