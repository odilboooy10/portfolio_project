from django.contrib import admin
from .models import Vendor, PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'email', 'company')
    ordering = ('name',)


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    fields = ('variant', 'quantity', 'unit_price', 'received_qty', 'description')
    readonly_fields = ('id', 'received_qty')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'vendor', 'status', 'expected_delivery', 'confirmed_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'vendor__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'reference', 'confirmed_at', 'created_at', 'updated_at', 'created_by')
    inlines = [PurchaseOrderLineInline]


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0
    fields = ('purchase_order_line', 'quantity_received')
    readonly_fields = ('id',)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('reference', 'purchase_order', 'warehouse', 'received_by', 'received_at')
    search_fields = ('reference', 'purchase_order__reference')
    ordering = ('-received_at',)
    readonly_fields = ('id', 'reference', 'received_at', 'received_by')
    inlines = [ReceiptLineInline]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
