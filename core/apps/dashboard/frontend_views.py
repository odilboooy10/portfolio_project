import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.views import View


class DashboardView(LoginRequiredMixin, View):
    login_url = '/login/'
    template_name = 'dashboard/index.html'

    def get(self, request):
        from apps.sales.models import SaleOrder, Invoice
        from apps.purchase.models import PurchaseOrder
        from apps.crm.models import Lead, Activity
        from apps.inventory.models import StockLevel

        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        # ── Revenue ──────────────────────────────────────────────────────────
        paid_invoices = Invoice.objects.filter(status='paid')
        revenue_this_month = paid_invoices.filter(paid_at__gte=this_month_start).aggregate(
            total=Sum(F('lines__quantity') * F('lines__unit_price'))
        )['total'] or Decimal('0')

        revenue_last_month = paid_invoices.filter(
            paid_at__gte=last_month_start, paid_at__lt=this_month_start
        ).aggregate(
            total=Sum(F('lines__quantity') * F('lines__unit_price'))
        )['total'] or Decimal('0')

        mom_change = None
        if revenue_last_month:
            mom_change = round(((revenue_this_month - revenue_last_month) / revenue_last_month) * 100, 2)

        # ── Orders ───────────────────────────────────────────────────────────
        orders = {o['status']: o['count'] for o in SaleOrder.objects.values('status').annotate(count=Count('id'))}

        # ── Summary dict (mirrors API response) ──────────────────────────────
        summary = {
            'revenue': {
                'this_month': revenue_this_month,
                'last_month': revenue_last_month,
                'mom_change_pct': mom_change,
            },
            'orders': {
                'confirmed': orders.get('confirmed', 0),
                'in_progress': orders.get('in_progress', 0),
                'done': orders.get('done', 0),
                'cancelled': orders.get('cancelled', 0),
            },
            'invoices': {
                'overdue': Invoice.objects.filter(status='issued', due_date__lt=now.date()).count(),
            },
            'purchases': {
                'pending': PurchaseOrder.objects.filter(status__in=['rfq', 'confirmed']).count(),
            },
            'crm': {
                'open_leads': Lead.objects.filter(won_at__isnull=True, lost_at__isnull=True).count(),
                'won_this_month': Lead.objects.filter(won_at__gte=this_month_start).count(),
            },
            'inventory': {
                'low_stock_variants': StockLevel.objects.filter(quantity__lte=5).count(),
            },
        }

        # ── Revenue chart (last 12 months) ───────────────────────────────────
        since = now - timedelta(days=365)
        chart_qs = (
            paid_invoices
            .filter(paid_at__gte=since)
            .annotate(month=TruncMonth('paid_at'))
            .values('month')
            .annotate(revenue=Sum(F('lines__quantity') * F('lines__unit_price')))
            .order_by('month')
        )
        chart_labels = [entry['month'].strftime('%b %Y') for entry in chart_qs]
        chart_data = [float(entry['revenue'] or 0) for entry in chart_qs]

        # ── Low stock ────────────────────────────────────────────────────────
        low_stock_qs = (
            StockLevel.objects
            .filter(quantity__lte=5)
            .select_related('variant__product', 'warehouse')
            .order_by('quantity')[:20]
        )
        low_stock = [
            {
                'product_name': sl.variant.product.name,
                'variant_sku': sl.variant.sku,
                'warehouse': sl.warehouse.name,
                'quantity': sl.quantity,
            }
            for sl in low_stock_qs
        ]

        # ── Order pipeline ───────────────────────────────────────────────────
        order_pipeline = list(
            SaleOrder.objects
            .values('status')
            .annotate(count=Count('id'), total_revenue=Sum(F('lines__quantity') * F('lines__unit_price')))
            .order_by('status')
        )

        # ── Recent activity ──────────────────────────────────────────────────
        events = []
        for order in SaleOrder.objects.select_related('customer').order_by('-confirmed_at')[:10]:
            if order.confirmed_at:
                events.append({
                    'type': 'sale_order',
                    'description': f"Sale order {order.reference} — {order.customer.name} ({order.status})",
                    'timestamp': order.confirmed_at,
                })
        for inv in Invoice.objects.select_related('customer').order_by('-created_at')[:10]:
            events.append({
                'type': 'invoice',
                'description': f"Invoice {inv.reference} — {inv.customer.name} ({inv.status})",
                'timestamp': inv.created_at,
            })
        for po in PurchaseOrder.objects.select_related('vendor').order_by('-created_at')[:10]:
            events.append({
                'type': 'purchase_order',
                'description': f"PO {po.reference} — {po.vendor.name} ({po.status})",
                'timestamp': po.created_at,
            })
        events.sort(key=lambda e: e['timestamp'] or now, reverse=True)

        return render(request, self.template_name, {
            'summary': summary,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'low_stock': low_stock,
            'order_pipeline': order_pipeline,
            'recent_activity': events[:15],
        })
