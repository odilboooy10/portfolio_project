from django.contrib import admin
from .models import (
    Category, ProductAttribute, ProductAttributeValue,
    Product, ProductVariant, Warehouse, StockMove, StockLevel,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('attribute', 'value')
    list_filter = ('attribute',)
    search_fields = ('value',)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'price_override', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'base_price', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'sku')
    ordering = ('name',)
    inlines = [ProductVariantInline]
    filter_horizontal = ('attributes',)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'effective_price', 'is_active')
    list_filter = ('is_active', 'product')
    search_fields = ('sku', 'product__name')
    filter_horizontal = ('attribute_values',)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ('move_type', 'variant', 'warehouse', 'quantity', 'reference', 'created_at', 'created_by')
    list_filter = ('move_type', 'warehouse')
    search_fields = ('variant__sku', 'reference')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'created_by')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ('variant', 'warehouse', 'quantity', 'updated_at')
    list_filter = ('warehouse',)
    search_fields = ('variant__sku', 'warehouse__name')
    readonly_fields = ('id', 'updated_at')
