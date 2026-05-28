from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import AccountingPermission
from .models import Account, Journal, JournalEntry, Payment
from .serializers import (
    AccountSerializer, JournalSerializer,
    JournalEntryListSerializer, JournalEntryDetailSerializer,
    PaymentSerializer,
)
from .tasks import send_payment_confirmation


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [AccountingPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name', 'account_type']
    ordering = ['code']

    def get_queryset(self):
        qs = Account.objects.select_related('parent')
        account_type = self.request.query_params.get('type')
        if account_type:
            qs = qs.filter(account_type=account_type)
        if not self.request.user.is_manager:
            qs = qs.filter(is_active=True)
        return qs


class JournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    permission_classes = [AccountingPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']

    def get_queryset(self):
        qs = Journal.objects.select_related('default_account')
        journal_type = self.request.query_params.get('type')
        if journal_type:
            qs = qs.filter(journal_type=journal_type)
        return qs


class JournalEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [AccountingPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'note']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        qs = JournalEntry.objects.select_related('journal', 'created_by').prefetch_related('lines__account')
        journal_id = self.request.query_params.get('journal')
        entry_status = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if journal_id:
            qs = qs.filter(journal_id=journal_id)
        if entry_status:
            qs = qs.filter(status=entry_status)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return JournalEntryListSerializer
        return JournalEntryDetailSerializer

    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        """Post a draft journal entry — locks it from further editing."""
        entry = self.get_object()
        if entry.status != JournalEntry.Status.DRAFT:
            return Response(
                {'detail': f'Cannot post an entry in status "{entry.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not entry.is_balanced:
            return Response(
                {'detail': f'Entry does not balance. Debit {entry.total_debit} ≠ Credit {entry.total_credit}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry.status = JournalEntry.Status.POSTED
        entry.save()
        return Response(JournalEntryDetailSerializer(entry, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a draft journal entry."""
        entry = self.get_object()
        if entry.status == JournalEntry.Status.POSTED:
            return Response(
                {'detail': 'Posted entries cannot be cancelled directly. Create a reversal entry.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry.status = JournalEntry.Status.CANCELLED
        entry.save()
        return Response(JournalEntryDetailSerializer(entry, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Create a reversal journal entry for a posted entry."""
        from django.utils import timezone

        entry = self.get_object()
        if entry.status != JournalEntry.Status.POSTED:
            return Response(
                {'detail': 'Only posted entries can be reversed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reversal = JournalEntry.objects.create(
            journal=entry.journal,
            date=request.data.get('date', timezone.now().date()),
            note=f"Reversal of {entry.reference}",
            created_by=request.user,
        )
        for line in entry.lines.all():
            JournalEntryLine = line.__class__
            JournalEntryLine.objects.create(
                entry=reversal,
                account=line.account,
                description=f"Reversal: {line.description}",
                debit=line.credit,   # swap debit/credit
                credit=line.debit,
            )

        return Response(
            JournalEntryDetailSerializer(reversal, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [AccountingPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'note']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def perform_create(self, serializer):
        payment = serializer.save(created_by=self.request.user)
        send_payment_confirmation.delay(str(payment.id))

    def get_queryset(self):
        qs = Payment.objects.select_related('journal', 'invoice', 'purchase_order', 'created_by')
        payment_type = self.request.query_params.get('type')
        journal_id = self.request.query_params.get('journal')
        invoice_id = self.request.query_params.get('invoice')
        po_id = self.request.query_params.get('purchase_order')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if payment_type:
            qs = qs.filter(payment_type=payment_type)
        if journal_id:
            qs = qs.filter(journal_id=journal_id)
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        if po_id:
            qs = qs.filter(purchase_order_id=po_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs
