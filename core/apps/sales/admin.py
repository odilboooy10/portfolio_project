from django.contrib import admin
from .models import (
    Customer, Quotation, QuotationLine,
    SaleOrder, SaleOrderLine, Invoice, InvoiceLine,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'email', 'company')
    ordering = ('name',)


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0
    fields = ('variant', 'quantity', 'unit_price', 'description')
    readonly_fields = ('id',)


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer', 'status', 'discount', 'validity_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'customer__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'reference', 'created_at', 'updated_at', 'created_by')
    inlines = [QuotationLineInline]


class SaleOrderLineInline(admin.TabularInline):
    model = SaleOrderLine
    extra = 0
    fields = ('variant', 'quantity', 'unit_price', 'description')
    readonly_fields = ('id',)


@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer', 'status', 'discount', 'confirmed_at')
    list_filter = ('status',)
    search_fields = ('reference', 'customer__name')
    ordering = ('-confirmed_at',)
    readonly_fields = ('id', 'reference', 'confirmed_at', 'updated_at', 'confirmed_by')
    inlines = [SaleOrderLineInline]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = ('variant', 'quantity', 'unit_price', 'description')
    readonly_fields = ('id',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer', 'status', 'issue_date', 'due_date', 'paid_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'customer__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'reference', 'paid_at', 'created_at', 'updated_at', 'created_by')
    inlines = [InvoiceLineInline]
