from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import SalesPermission
from .tasks import send_invoice_pdf_email
from .models import Customer, Quotation, SaleOrder, Invoice
from .serializers import (
    CustomerSerializer,
    QuotationListSerializer, QuotationDetailSerializer,
    SaleOrderListSerializer, SaleOrderDetailSerializer,
    InvoiceListSerializer, InvoiceDetailSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [SalesPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'company']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        qs = Customer.objects.all()
        if not self.request.user.is_manager:
            qs = qs.filter(is_active=True)
        return qs


class QuotationViewSet(viewsets.ModelViewSet):
    permission_classes = [SalesPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'customer__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Quotation.objects.select_related('customer', 'created_by').prefetch_related('lines__variant__product')
        status_filter = self.request.query_params.get('status')
        customer_id = self.request.query_params.get('customer')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return QuotationListSerializer
        return QuotationDetailSerializer

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark quotation as sent to customer."""
        quotation = self.get_object()
        if quotation.status != Quotation.Status.DRAFT:
            return Response(
                {'detail': f'Cannot send a quotation in status "{quotation.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = Quotation.Status.SENT
        quotation.save()
        return Response(QuotationDetailSerializer(quotation, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm quotation and create a SaleOrder from it."""
        quotation = self.get_object()
        if quotation.status not in (Quotation.Status.DRAFT, Quotation.Status.SENT):
            return Response(
                {'detail': f'Cannot confirm a quotation in status "{quotation.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not quotation.lines.exists():
            return Response(
                {'detail': 'Cannot confirm a quotation with no lines.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quotation.status = Quotation.Status.CONFIRMED
        quotation.save()

        order = SaleOrder.objects.create(
            quotation=quotation,
            customer=quotation.customer,
            discount=quotation.discount,
            note=quotation.note,
            confirmed_by=request.user,
        )
        for line in quotation.lines.all():
            order.lines.create(
                variant=line.variant,
                quantity=line.quantity,
                unit_price=line.unit_price,
                description=line.description,
            )

        serializer = SaleOrderDetailSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a draft or sent quotation."""
        quotation = self.get_object()
        if quotation.status not in (Quotation.Status.DRAFT, Quotation.Status.SENT):
            return Response(
                {'detail': f'Cannot cancel a quotation in status "{quotation.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = Quotation.Status.CANCELLED
        quotation.save()
        return Response(QuotationDetailSerializer(quotation, context={'request': request}).data)


class SaleOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [SalesPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'customer__name']
    ordering_fields = ['confirmed_at', 'status']
    ordering = ['-confirmed_at']

    def get_queryset(self):
        qs = SaleOrder.objects.select_related('customer', 'quotation', 'confirmed_by').prefetch_related('lines__variant__product')
        status_filter = self.request.query_params.get('status')
        customer_id = self.request.query_params.get('customer')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleOrderListSerializer
        return SaleOrderDetailSerializer

    @action(detail=True, methods=['post'])
    def invoice(self, request, pk=None):
        """Create an invoice from this sale order."""
        order = self.get_object()
        if order.status == SaleOrder.Status.CANCELLED:
            return Response(
                {'detail': 'Cannot invoice a cancelled order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not order.lines.exists():
            return Response(
                {'detail': 'Cannot invoice an order with no lines.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inv = Invoice.objects.create(
            sale_order=order,
            customer=order.customer,
            discount=order.discount,
            note=order.note,
            created_by=request.user,
        )
        for line in order.lines.all():
            inv.lines.create(
                variant=line.variant,
                quantity=line.quantity,
                unit_price=line.unit_price,
                description=line.description,
            )

        serializer = InvoiceDetailSerializer(inv, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == SaleOrder.Status.DONE:
            return Response(
                {'detail': 'Cannot cancel a completed order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = SaleOrder.Status.CANCELLED
        order.save()
        return Response(SaleOrderDetailSerializer(order, context={'request': request}).data)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [SalesPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'customer__name']
    ordering_fields = ['created_at', 'due_date', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Invoice.objects.select_related('customer', 'sale_order', 'created_by').prefetch_related('lines__variant__product')
        status_filter = self.request.query_params.get('status')
        customer_id = self.request.query_params.get('customer')
        overdue = self.request.query_params.get('overdue')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if overdue:
            from django.utils.timezone import now
            qs = qs.filter(due_date__lt=now().date(), status=Invoice.Status.ISSUED)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceDetailSerializer

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Mark invoice as issued (sent to customer)."""
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {'detail': f'Cannot issue an invoice in status "{invoice.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.ISSUED
        invoice.issue_date = timezone.now().date()
        invoice.save()
        send_invoice_pdf_email.delay(str(invoice.id))
        return Response(InvoiceDetailSerializer(invoice, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Record payment for an issued invoice."""
        invoice = self.get_object()
        if invoice.status != Invoice.Status.ISSUED:
            return Response(
                {'detail': f'Cannot mark as paid an invoice in status "{invoice.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.save()

        # Mark the linked sale order as done if all its invoices are paid
        if invoice.sale_order:
            all_paid = not invoice.sale_order.invoices.exclude(status=Invoice.Status.PAID).exists()
            if all_paid:
                invoice.sale_order.status = SaleOrder.Status.DONE
                invoice.sale_order.save()

        return Response(InvoiceDetailSerializer(invoice, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            return Response(
                {'detail': 'Cannot cancel a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.CANCELLED
        invoice.save()
        return Response(InvoiceDetailSerializer(invoice, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """Render invoice as PDF and return as a download."""
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        import weasyprint

        invoice = self.get_object()
        html = render_to_string('pdf/invoice.html', {'invoice': invoice}, request=request)
        pdf_bytes = weasyprint.HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.reference}.pdf"'
        return response
