from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.sales.models import Invoice, SaleOrder


class OrderListView(LoginRequiredMixin, ListView):
    model = SaleOrder
    template_name = 'sales/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        qs = SaleOrder.objects.select_related('customer', 'confirmed_by')
        status = self.request.GET.get('status')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(reference__icontains=q) | qs.filter(customer__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = SaleOrder.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['total_count'] = SaleOrder.objects.count()
        return ctx


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = SaleOrder
    template_name = 'sales/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return SaleOrder.objects.select_related('customer', 'confirmed_by', 'quotation').prefetch_related('lines__variant__product')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipeline'] = [
            ('confirmed',   'Confirmed'),
            ('in_progress', 'In Progress'),
            ('done',        'Done'),
        ]
        return ctx


class OrderMarkInProgressView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(SaleOrder, pk=pk)
        if order.status == SaleOrder.Status.CONFIRMED:
            order.status = SaleOrder.Status.IN_PROGRESS
            order.save(update_fields=['status'])
            messages.success(request, f'{order.reference} marked as In Progress.')
        return redirect('sales:order-detail', pk=pk)


class OrderMarkDoneView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(SaleOrder, pk=pk)
        if order.status == SaleOrder.Status.IN_PROGRESS:
            order.status = SaleOrder.Status.DONE
            order.save(update_fields=['status'])
            messages.success(request, f'{order.reference} marked as Done.')
        return redirect('sales:order-detail', pk=pk)


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(SaleOrder, pk=pk)
        if order.status in (SaleOrder.Status.CONFIRMED, SaleOrder.Status.IN_PROGRESS):
            order.status = SaleOrder.Status.CANCELLED
            order.save(update_fields=['status'])
            messages.warning(request, f'{order.reference} has been cancelled.')
        return redirect('sales:order-detail', pk=pk)


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = Invoice.objects.select_related('customer', 'sale_order')
        status = self.request.GET.get('status')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(reference__icontains=q) | qs.filter(customer__name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Invoice.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        return Invoice.objects.select_related('customer', 'sale_order', 'created_by').prefetch_related('lines__variant__product')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipeline'] = [
            ('draft',     'Draft'),
            ('issued',    'Issued'),
            ('paid',      'Paid'),
        ]
        return ctx


class InvoiceMarkIssuedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status == Invoice.Status.DRAFT:
            invoice.status = Invoice.Status.ISSUED
            from django.utils import timezone
            invoice.issue_date = timezone.now().date()
            invoice.save(update_fields=['status', 'issue_date'])
            messages.success(request, f'{invoice.reference} has been issued.')
        return redirect('sales:invoice-detail', pk=pk)


class InvoiceMarkPaidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status == Invoice.Status.ISSUED:
            invoice.status = Invoice.Status.PAID
            from django.utils import timezone
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['status', 'paid_at'])
            messages.success(request, f'{invoice.reference} marked as Paid.')
        return redirect('sales:invoice-detail', pk=pk)


class InvoiceCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status in (Invoice.Status.DRAFT, Invoice.Status.ISSUED):
            invoice.status = Invoice.Status.CANCELLED
            invoice.save(update_fields=['status'])
            messages.warning(request, f'{invoice.reference} has been cancelled.')
        return redirect('sales:invoice-detail', pk=pk)
