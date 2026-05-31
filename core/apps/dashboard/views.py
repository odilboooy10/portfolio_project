from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from apps.users.permissions import IsManager


class DashboardSummaryView(APIView):
    """
    Top-level KPI snapshot — one call, all the numbers.
    """
    permission_classes = [IsManager]

    def get(self, request):
        from apps.sales.models import SaleOrder, Invoice
        from apps.purchase.models import PurchaseOrder
        from apps.crm.models import Lead
        from apps.inventory.models import StockLevel

        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        # ── Revenue ──────────────────────────────────────────────────────────
        paid_invoices = Invoice.objects.filter(status='paid')
        revenue_total = paid_invoices.aggregate(
            total=Sum(F('lines__quantity') * F('lines__unit_price'))
        )['total'] or Decimal('0')

        revenue_this_month = paid_invoices.filter(paid_at__gte=this_month_start).aggregate(
            total=Sum(F('lines__quantity') * F('lines__unit_price'))
        )['total'] or Decimal('0')

        revenue_last_month = paid_invoices.filter(
            paid_at__gte=last_month_start, paid_at__lt=this_month_start
        ).aggregate(
            total=Sum(F('lines__quantity') * F('lines__unit_price'))
        )['total'] or Decimal('0')

        # ── Orders ───────────────────────────────────────────────────────────
        orders = SaleOrder.objects.values('status').annotate(count=Count('id'))
        order_counts = {o['status']: o['count'] for o in orders}

        # ── Invoices ─────────────────────────────────────────────────────────
        overdue_count = Invoice.objects.filter(
            status='issued', due_date__lt=now.date()
        ).count()

        # ── Purchases ────────────────────────────────────────────────────────
        pending_po_count = PurchaseOrder.objects.filter(
            status__in=['rfq', 'confirmed']
        ).count()

        # ── CRM ──────────────────────────────────────────────────────────────
        open_leads = Lead.objects.filter(won_at__isnull=True, lost_at__isnull=True).count()
        won_this_month = Lead.objects.filter(won_at__gte=this_month_start).count()

        # ── Inventory ────────────────────────────────────────────────────────
        low_stock_count = StockLevel.objects.filter(quantity__lte=5).count()

        return Response({
            'revenue': {
                'total': revenue_total,
                'this_month': revenue_this_month,
                'last_month': revenue_last_month,
                'mom_change_pct': _percent_change(revenue_last_month, revenue_this_month),
            },
            'orders': {
                'confirmed': order_counts.get('confirmed', 0),
                'in_progress': order_counts.get('in_progress', 0),
                'done': order_counts.get('done', 0),
                'cancelled': order_counts.get('cancelled', 0),
            },
            'invoices': {
                'overdue': overdue_count,
            },
            'purchases': {
                'pending': pending_po_count,
            },
            'crm': {
                'open_leads': open_leads,
                'won_this_month': won_this_month,
            },
            'inventory': {
                'low_stock_variants': low_stock_count,
            },
        })


class RevenueChartView(APIView):
    """Monthly revenue for the last N months (default 12)."""
    permission_classes = [IsManager]

    def get(self, request):
        from apps.sales.models import Invoice

        months = min(int(request.query_params.get('months', 12)), 24)
        since = timezone.now() - timedelta(days=months * 31)

        data = (
            Invoice.objects
            .filter(status='paid', paid_at__gte=since)
            .annotate(month=TruncMonth('paid_at'))
            .values('month')
            .annotate(revenue=Sum(F('lines__quantity') * F('lines__unit_price')))
            .order_by('month')
        )

        return Response([
            {'month': entry['month'].strftime('%Y-%m'), 'revenue': entry['revenue'] or 0}
            for entry in data
        ])


class TopProductsView(APIView):
    """Top N products by quantity sold."""
    permission_classes = [IsManager]

    def get(self, request):
        from apps.sales.models import SaleOrderLine

        limit = min(int(request.query_params.get('limit', 10)), 50)

        data = (
            SaleOrderLine.objects
            .filter(order__status__in=['confirmed', 'in_progress', 'done'])
            .values(
                product_name=F('variant__product__name'),
                variant_sku=F('variant__sku'),
            )
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price')),
            )
            .order_by('-total_qty')[:limit]
        )

        return Response(list(data))


class LowStockView(APIView):
    """Variants with stock at or below the threshold (default ≤ 5)."""
    permission_classes = [IsManager]

    def get(self, request):
        from apps.inventory.models import StockLevel

        threshold = int(request.query_params.get('threshold', 5))

        data = (
            StockLevel.objects
            .filter(quantity__lte=threshold)
            .select_related('variant__product', 'warehouse')
            .order_by('quantity')
        )

        return Response([
            {
                'variant_id': str(sl.variant_id),
                'variant_sku': sl.variant.sku,
                'product_name': sl.variant.product.name,
                'warehouse': sl.warehouse.name,
                'quantity': sl.quantity,
            }
            for sl in data
        ])


class RecentActivityView(APIView):
    """Latest actions across all modules, merged and sorted by time."""
    permission_classes = [IsManager]

    def get(self, request):
        from apps.sales.models import SaleOrder, Invoice
        from apps.purchase.models import PurchaseOrder
        from apps.crm.models import Activity

        limit = min(int(request.query_params.get('limit', 20)), 100)

        events = []

        for order in SaleOrder.objects.order_by('-confirmed_at')[:limit]:
            events.append({
                'type': 'sale_order',
                'reference': order.reference,
                'description': f"Sale order {order.reference} — {order.customer.name} ({order.status})",
                'timestamp': order.confirmed_at,
            })

        for inv in Invoice.objects.order_by('-created_at')[:limit]:
            events.append({
                'type': 'invoice',
                'reference': inv.reference,
                'description': f"Invoice {inv.reference} — {inv.customer.name} ({inv.status})",
                'timestamp': inv.created_at,
            })

        for po in PurchaseOrder.objects.order_by('-created_at')[:limit]:
            events.append({
                'type': 'purchase_order',
                'reference': po.reference,
                'description': f"Purchase order {po.reference} — {po.vendor.name} ({po.status})",
                'timestamp': po.created_at,
            })

        for act in Activity.objects.filter(is_done=False).order_by('due_date')[:limit]:
            events.append({
                'type': 'crm_activity',
                'reference': str(act.id),
                'description': f"[{act.get_activity_type_display()}] {act.title} — {act.lead.name}",
                'timestamp': act.due_date or act.created_at,
            })

        events.sort(key=lambda e: e['timestamp'] or timezone.now(), reverse=True)

        return Response(events[:limit])


class OrderPipelineView(APIView):
    """Sale order counts and revenue per status."""
    permission_classes = [IsManager]

    def get(self, request):
        from apps.sales.models import SaleOrder

        data = (
            SaleOrder.objects
            .values('status')
            .annotate(
                count=Count('id'),
                total_revenue=Sum(F('lines__quantity') * F('lines__unit_price')),
            )
            .order_by('status')
        )

        return Response(list(data))


def _percent_change(old, new):
    if not old:
        return None
    return round(((new - old) / old) * 100, 2)
