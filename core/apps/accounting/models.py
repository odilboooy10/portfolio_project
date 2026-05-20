import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Account(models.Model):
    """Chart of accounts entry."""
    class AccountType(models.TextChoices):
        ASSET = 'asset', 'Asset'
        LIABILITY = 'liability', 'Liability'
        EQUITY = 'equity', 'Equity'
        REVENUE = 'revenue', 'Revenue'
        EXPENSE = 'expense', 'Expense'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.name}"


class Journal(models.Model):
    """Groups journal entries by type (sales, purchases, bank, cash, etc.)."""
    class JournalType(models.TextChoices):
        SALES = 'sales', 'Sales'
        PURCHASE = 'purchase', 'Purchase'
        BANK = 'bank', 'Bank'
        CASH = 'cash', 'Cash'
        GENERAL = 'general', 'General'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    journal_type = models.CharField(max_length=20, choices=JournalType.choices)
    default_account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='journals'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class JournalEntry(models.Model):
    """Double-entry bookkeeping entry. Must balance (debits == credits)."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name='entries')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    date = models.DateField()
    note = models.TextField(blank=True)

    # Optional links to source documents
    invoice = models.ForeignKey(
        'sales.Invoice', null=True, blank=True, on_delete=models.SET_NULL, related_name='journal_entries'
    )
    purchase_order = models.ForeignKey(
        'purchase.PurchaseOrder', null=True, blank=True, on_delete=models.SET_NULL, related_name='journal_entries'
    )

    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='journal_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        return f"{self.reference} ({self.date})"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = JournalEntry.objects.order_by('-created_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"JE-{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalEntryLine(models.Model):
    """Single debit or credit line within a journal entry."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entry_lines')
    description = models.CharField(max_length=500, blank=True)
    debit = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    credit = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.account} | Dr {self.debit} | Cr {self.credit}"


class Payment(models.Model):
    """Records a payment in or out, linked to an invoice or purchase order."""
    class PaymentType(models.TextChoices):
        INBOUND = 'inbound', 'Inbound (Customer)'
        OUTBOUND = 'outbound', 'Outbound (Vendor)'

    class PaymentMethod(models.TextChoices):
        BANK = 'bank', 'Bank Transfer'
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, editable=False)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK)
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    date = models.DateField()
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name='payments')
    invoice = models.ForeignKey(
        'sales.Invoice', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments'
    )
    purchase_order = models.ForeignKey(
        'purchase.PurchaseOrder', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments'
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.reference} — {self.payment_type} {self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last = Payment.objects.order_by('-created_at').first()
            next_num = (int(last.reference.split('-')[1]) + 1) if last else 1
            self.reference = f"PAY-{next_num:05d}"
        super().save(*args, **kwargs)
