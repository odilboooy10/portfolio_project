from django.utils import timezone
from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import PurchasePermission
from .models import Vendor, PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine
from .serializers import (
    VendorSerializer,
    PurchaseOrderListSerializer, PurchaseOrderDetailSerializer,
    ReceiptSerializer,
)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [PurchasePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'company']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        qs = Vendor.objects.all()
        if not self.request.user.is_manager:
            qs = qs.filter(is_active=True)
        return qs


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [PurchasePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'vendor__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related('vendor', 'created_by').prefetch_related(
            'lines__variant__product'
        )
        status_filter = self.request.query_params.get('status')
        vendor_id = self.request.query_params.get('vendor')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseOrderListSerializer
        return PurchaseOrderDetailSerializer

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm RFQ into a Purchase Order."""
        order = self.get_object()
        if order.status != PurchaseOrder.Status.RFQ:
            return Response(
                {'detail': f'Cannot confirm an order in status "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not order.lines.exists():
            return Response(
                {'detail': 'Cannot confirm an order with no lines.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = PurchaseOrder.Status.CONFIRMED
        order.confirmed_at = timezone.now()
        order.save()
        return Response(PurchaseOrderDetailSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status in (PurchaseOrder.Status.RECEIVED, PurchaseOrder.Status.BILLED):
            return Response(
                {'detail': f'Cannot cancel an order in status "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = PurchaseOrder.Status.CANCELLED
        order.save()
        return Response(PurchaseOrderDetailSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def receive(self, request, pk=None):
        """
        Receive goods against this PO. Creates a Receipt, updates received_qty
        on each line, moves stock into inventory, and advances the PO status.

        Expects: { warehouse, lines: [{purchase_order_line, quantity_received}], note }
        """
        order = self.get_object()
        if order.status not in (PurchaseOrder.Status.CONFIRMED, PurchaseOrder.Status.RECEIVED):
            return Response(
                {'detail': f'Cannot receive goods for an order in status "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        warehouse_id = request.data.get('warehouse')
        lines_data = request.data.get('lines', [])
        note = request.data.get('note', '')

        if not warehouse_id:
            return Response({'detail': 'warehouse is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not lines_data:
            return Response({'detail': 'lines cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        receipt = Receipt.objects.create(
            purchase_order=order,
            warehouse_id=warehouse_id,
            note=note,
            received_by=request.user,
        )

        from apps.inventory.models import StockMove, StockLevel

        for entry in lines_data:
            po_line_id = entry.get('purchase_order_line')
            qty = entry.get('quantity_received')

            if not po_line_id or qty is None:
                raise ValueError('Each line needs purchase_order_line and quantity_received.')

            from decimal import Decimal
            qty = Decimal(str(qty))

            po_line = PurchaseOrderLine.objects.get(pk=po_line_id, order=order)

            ReceiptLine.objects.create(
                receipt=receipt,
                purchase_order_line=po_line,
                quantity_received=qty,
            )

            # Update received quantity on the PO line
            PurchaseOrderLine.objects.filter(pk=po_line.pk).update(
                received_qty=F('received_qty') + qty
            )

            # Create a stock IN move
            move = StockMove.objects.create(
                variant=po_line.variant,
                warehouse_id=warehouse_id,
                move_type=StockMove.MoveType.IN,
                quantity=qty,
                reference=receipt.reference,
                note=f"Received via {order.reference}",
                created_by=request.user,
            )

            # Update StockLevel cache
            stock_level, _ = StockLevel.objects.get_or_create(
                variant=po_line.variant,
                warehouse_id=warehouse_id,
                defaults={'quantity': 0},
            )
            StockLevel.objects.filter(pk=stock_level.pk).update(
                quantity=F('quantity') + qty
            )

        # Advance PO status
        order.refresh_from_db()
        all_received = all(
            line.received_qty >= line.quantity for line in order.lines.all()
        )
        order.status = PurchaseOrder.Status.RECEIVED if all_received else PurchaseOrder.Status.CONFIRMED
        order.save()

        return Response(
            ReceiptSerializer(receipt, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def bill(self, request, pk=None):
        """Mark purchase order as billed."""
        order = self.get_object()
        if order.status != PurchaseOrder.Status.RECEIVED:
            return Response(
                {'detail': f'Cannot bill an order in status "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = PurchaseOrder.Status.BILLED
        order.save()
        return Response(PurchaseOrderDetailSerializer(order, context={'request': request}).data)


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    """Receipts are created via PurchaseOrder.receive action — read-only here."""
    serializer_class = ReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-received_at']

    def get_queryset(self):
        qs = Receipt.objects.select_related(
            'purchase_order__vendor', 'warehouse', 'received_by'
        ).prefetch_related('lines__purchase_order_line__variant__product')
        po_id = self.request.query_params.get('purchase_order')
        warehouse_id = self.request.query_params.get('warehouse')
        if po_id:
            qs = qs.filter(purchase_order_id=po_id)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs
