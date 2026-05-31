from django.contrib import admin
from .models import Account, Journal, JournalEntry, JournalEntryLine, Payment


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'parent', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'journal_type', 'default_account', 'is_active')
    list_filter = ('journal_type', 'is_active')
    search_fields = ('code', 'name')


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0
    fields = ('account', 'description', 'debit', 'credit')
    readonly_fields = ('id',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'journal', 'status', 'date', 'total_debit', 'is_balanced', 'created_at')
    list_filter = ('status', 'journal')
    search_fields = ('reference', 'note')
    ordering = ('-date',)
    readonly_fields = ('id', 'reference', 'created_at', 'updated_at', 'created_by')
    inlines = [JournalEntryLineInline]

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'posted':
            return False
        return super().has_change_permission(request, obj)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'payment_type', 'payment_method', 'amount', 'date', 'journal', 'created_at')
    list_filter = ('payment_type', 'payment_method', 'journal')
    search_fields = ('reference', 'note')
    ordering = ('-date',)
    readonly_fields = ('id', 'reference', 'created_at', 'created_by')
