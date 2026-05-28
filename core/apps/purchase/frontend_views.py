from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.inventory.models import StockLevel, StockMove, Warehouse
from apps.purchase.models import PurchaseOrder, Receipt, ReceiptLine, Vendor


class VendorListView(LoginRequiredMixin, ListView):
    model = Vendor
    template_name = 'purchase/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 30

    def get_queryset(self):
        qs = Vendor.objects.all()
        q = self.request.GET.get('q', '').strip()
        active = self.request.GET.get('active', '')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(company__icontains=q)
        if active == '1':
            qs = qs.filter(is_active=True)
        elif active == '0':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_active'] = self.request.GET.get('active', '')
        return ctx


class POListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'purchase/po_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related('vendor', 'created_by')
        status = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(reference__icontains=q) | qs.filter(vendor__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PurchaseOrder.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class PODetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'purchase/po_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return PurchaseOrder.objects.select_related(
            'vendor', 'created_by'
        ).prefetch_related('lines__variant__product', 'receipts__lines')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipeline'] = [
            ('rfq',       'RFQ'),
            ('confirmed', 'Confirmed'),
            ('received',  'Received'),
            ('billed',    'Billed'),
        ]
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        return ctx


class POConfirmView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status == PurchaseOrder.Status.RFQ:
            order.status = PurchaseOrder.Status.CONFIRMED
            order.confirmed_at = timezone.now()
            order.save(update_fields=['status', 'confirmed_at'])
            messages.success(request, f'{order.reference} confirmed as Purchase Order.')
        return redirect('purchase:po-detail', pk=pk)


class POCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status in (PurchaseOrder.Status.RFQ, PurchaseOrder.Status.CONFIRMED):
            order.status = PurchaseOrder.Status.CANCELLED
            order.save(update_fields=['status'])
            messages.warning(request, f'{order.reference} has been cancelled.')
        return redirect('purchase:po-detail', pk=pk)


class POMarkBilledView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status == PurchaseOrder.Status.RECEIVED:
            order.status = PurchaseOrder.Status.BILLED
            order.save(update_fields=['status'])
            messages.success(request, f'{order.reference} marked as Billed.')
        return redirect('purchase:po-detail', pk=pk)


class POReceiveView(LoginRequiredMixin, TemplateView):
    """GET: show receive form. POST: create receipt, update stock."""
    template_name = 'purchase/receive_form.html'

    def get_object(self):
        return get_object_or_404(
            PurchaseOrder.objects.prefetch_related('lines__variant__product'),
            pk=self.kwargs['pk'],
            status=PurchaseOrder.Status.CONFIRMED,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.get_object()
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        return ctx

    def post(self, request, pk):
        order = get_object_or_404(
            PurchaseOrder, pk=pk, status=PurchaseOrder.Status.CONFIRMED
        )
        warehouse_id = request.POST.get('warehouse')
        note = request.POST.get('note', '')

        if not warehouse_id:
            messages.error(request, 'Please select a warehouse.')
            return redirect('purchase:po-receive', pk=pk)

        # Build received quantities from POST data
        received = {}
        for line in order.lines.all():
            key = f'qty_{line.pk}'
            try:
                qty = float(request.POST.get(key, 0) or 0)
            except (ValueError, TypeError):
                qty = 0
            if qty > 0:
                received[line] = min(qty, float(line.remaining_qty))

        if not received:
            messages.error(request, 'Enter at least one received quantity.')
            return redirect('purchase:po-receive', pk=pk)

        # Create Receipt
        receipt = Receipt.objects.create(
            purchase_order=order,
            warehouse_id=warehouse_id,
            note=note,
            received_by=request.user,
        )

        for line, qty in received.items():
            # Receipt line
            ReceiptLine.objects.create(
                receipt=receipt,
                purchase_order_line=line,
                quantity_received=qty,
            )
            # Update PO line received qty
            line.received_qty = float(line.received_qty) + qty
            line.save(update_fields=['received_qty'])

            # Stock move (IN)
            StockMove.objects.create(
                variant=line.variant,
                warehouse_id=warehouse_id,
                move_type=StockMove.MoveType.IN,
                quantity=qty,
                reference=receipt.reference,
                note=f'Receipt from {order.reference}',
                created_by=request.user,
            )
            # Update StockLevel cache
            sl, _ = StockLevel.objects.get_or_create(
                variant=line.variant,
                warehouse_id=warehouse_id,
            )
            sl.quantity = float(sl.quantity) + qty
            sl.save(update_fields=['quantity'])

        # Mark PO as received if all lines fully received
        all_received = all(
            float(l.received_qty) >= float(l.quantity)
            for l in order.lines.all()
        )
        if all_received:
            order.status = PurchaseOrder.Status.RECEIVED
            order.save(update_fields=['status'])
            messages.success(request, f'{receipt.reference} saved. {order.reference} fully received.')
        else:
            messages.success(request, f'{receipt.reference} saved. Partial receipt recorded.')

        return redirect('purchase:po-detail', pk=pk)
