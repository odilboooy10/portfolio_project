from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.accounting.models import Account, Journal, JournalEntry, Payment


class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'accounting/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        qs = Account.objects.select_related('parent')
        q = self.request.GET.get('q', '').strip()
        account_type = self.request.GET.get('type', '')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
        if account_type:
            qs = qs.filter(account_type=account_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['account_types'] = Account.AccountType.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_type'] = self.request.GET.get('type', '')
        # Group by type for COA display — list of (val, label, [accounts])
        accounts_list = list(ctx['accounts'])
        ctx['grouped'] = [
            (t, label, [a for a in accounts_list if a.account_type == t])
            for t, label in Account.AccountType.choices
        ]
        return ctx


class JournalListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'accounting/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 30

    def get_queryset(self):
        qs = JournalEntry.objects.select_related('journal', 'created_by', 'invoice', 'purchase_order')
        status = self.request.GET.get('status', '')
        journal_id = self.request.GET.get('journal', '')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if journal_id:
            qs = qs.filter(journal_id=journal_id)
        if q:
            qs = qs.filter(reference__icontains=q) | qs.filter(note__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['journals'] = Journal.objects.filter(is_active=True)
        ctx['statuses'] = JournalEntry.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['current_journal'] = self.request.GET.get('journal', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class JournalDetailView(LoginRequiredMixin, DetailView):
    model = JournalEntry
    template_name = 'accounting/journal_detail.html'
    context_object_name = 'entry'

    def get_queryset(self):
        return JournalEntry.objects.select_related(
            'journal', 'created_by', 'invoice__customer', 'purchase_order__vendor'
        ).prefetch_related('lines__account')


class JournalPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status == JournalEntry.Status.DRAFT:
            if not entry.is_balanced:
                messages.error(request, f'Cannot post {entry.reference} — debits ≠ credits.')
                return redirect('accounting:journal-detail', pk=pk)
            entry.status = JournalEntry.Status.POSTED
            entry.save(update_fields=['status'])
            messages.success(request, f'{entry.reference} posted.')
        return redirect('accounting:journal-detail', pk=pk)


class JournalCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status == JournalEntry.Status.DRAFT:
            entry.status = JournalEntry.Status.CANCELLED
            entry.save(update_fields=['status'])
            messages.warning(request, f'{entry.reference} cancelled.')
        return redirect('accounting:journal-detail', pk=pk)


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'accounting/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 30

    def get_queryset(self):
        qs = Payment.objects.select_related(
            'journal', 'created_by', 'invoice__customer', 'purchase_order__vendor'
        )
        payment_type = self.request.GET.get('type', '')
        method = self.request.GET.get('method', '')
        q = self.request.GET.get('q', '').strip()
        if payment_type:
            qs = qs.filter(payment_type=payment_type)
        if method:
            qs = qs.filter(payment_method=method)
        if q:
            qs = qs.filter(reference__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['payment_types'] = Payment.PaymentType.choices
        ctx['payment_methods'] = Payment.PaymentMethod.choices
        ctx['current_type'] = self.request.GET.get('type', '')
        ctx['current_method'] = self.request.GET.get('method', '')
        ctx['q'] = self.request.GET.get('q', '')
        # Summary totals
        from django.db.models import Sum
        ctx['total_inbound'] = Payment.objects.filter(
            payment_type='inbound'
        ).aggregate(t=Sum('amount'))['t'] or 0
        ctx['total_outbound'] = Payment.objects.filter(
            payment_type='outbound'
        ).aggregate(t=Sum('amount'))['t'] or 0
        return ctx
