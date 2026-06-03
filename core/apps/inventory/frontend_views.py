from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.users.frontend_views import AdminRequiredMixin

from apps.inventory.models import (
    Category, Product, StockLevel, StockMove, Warehouse, ProductVariant
)

LOW_STOCK_THRESHOLD = 5


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 30

    def get_queryset(self):
        qs = Product.objects.select_related('category').prefetch_related('variants')
        q = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category')
        active = self.request.GET.get('active')

        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(sku__icontains=q)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if active == '1':
            qs = qs.filter(is_active=True)
        elif active == '0':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.filter(parent=None)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_category'] = self.request.GET.get('category', '')
        ctx['current_active'] = self.request.GET.get('active', '')
        return ctx


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('category').prefetch_related(
            'variants__attribute_values__attribute',
            'variants__stock_levels__warehouse',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        ctx['low_threshold'] = LOW_STOCK_THRESHOLD
        ctx['total_stock'] = StockLevel.objects.filter(
            variant__product=self.object
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ctx['categories'] = Category.objects.order_by('name')
        return ctx


class StockLevelListView(LoginRequiredMixin, ListView):
    model = StockLevel
    template_name = 'inventory/stock_levels.html'
    context_object_name = 'stock_levels'
    paginate_by = 40

    def get_queryset(self):
        qs = StockLevel.objects.select_related(
            'variant__product', 'warehouse'
        ).order_by('variant__product__name', 'warehouse__name')

        q = self.request.GET.get('q', '').strip()
        warehouse_id = self.request.GET.get('warehouse')
        low = self.request.GET.get('low')

        if q:
            qs = qs.filter(variant__product__name__icontains=q) | qs.filter(variant__sku__icontains=q)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if low == '1':
            qs = qs.filter(quantity__lte=LOW_STOCK_THRESHOLD)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_warehouse'] = self.request.GET.get('warehouse', '')
        ctx['current_low'] = self.request.GET.get('low', '')
        ctx['low_threshold'] = LOW_STOCK_THRESHOLD
        ctx['low_count'] = StockLevel.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD).count()
        return ctx


class StockMoveCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/stock_move_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['variants'] = ProductVariant.objects.filter(
            is_active=True
        ).select_related('product').order_by('product__name', 'sku')
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        ctx['move_types'] = StockMove.MoveType.choices
        return ctx

    def post(self, request):
        variant_id = request.POST.get('variant')
        warehouse_id = request.POST.get('warehouse')
        move_type = request.POST.get('move_type')
        note = request.POST.get('note', '')
        reference = request.POST.get('reference', '')

        try:
            qty = abs(float(request.POST.get('quantity', 0)))
        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity.')
            return redirect('inventory:stock-move-create')

        if move_type == StockMove.MoveType.OUT:
            qty = -qty

        try:
            move = StockMove(
                variant_id=variant_id,
                warehouse_id=warehouse_id,
                move_type=move_type,
                quantity=qty,
                reference=reference,
                note=note,
                created_by=request.user,
            )
            move.full_clean()
            move.save()

            # Update StockLevel cache
            sl, _ = StockLevel.objects.get_or_create(
                variant_id=variant_id,
                warehouse_id=warehouse_id,
            )
            sl.quantity = (sl.quantity or 0) + qty
            sl.save(update_fields=['quantity'])

            messages.success(request, f'Stock move recorded — {move}')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            return redirect('inventory:stock-move-create')

        return redirect('inventory:stock-levels')


def _product_values(post=None, product=None):
    """Build a flat values dict for the product form template."""
    if post:
        return {
            'name': post.get('name', ''),
            'sku': post.get('sku', ''),
            'base_price': post.get('base_price', ''),
            'category': post.get('category', ''),
            'description': post.get('description', ''),
            'is_active': post.get('is_active') == 'on',
            'initial_qty': post.get('initial_qty', '0'),
        }
    if product:
        return {
            'name': product.name,
            'sku': product.sku,
            'base_price': product.base_price,
            'category': str(product.category_id) if product.category_id else '',
            'description': product.description,
            'is_active': product.is_active,
            'initial_qty': '0',
        }
    return {'name': '', 'sku': '', 'base_price': '', 'category': '', 'description': '', 'is_active': True, 'initial_qty': '0'}


class ProductCreateView(AdminRequiredMixin, View):
    template_name = 'inventory/product_form.html'

    def get(self, request):
        ctx = {
            'categories': Category.objects.order_by('name'),
            'action': 'Create',
            'values': _product_values(),
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        name = request.POST.get('name', '').strip()
        sku = request.POST.get('sku', '').strip()
        base_price = request.POST.get('base_price', '').strip()
        category_id = request.POST.get('category') or None
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')
        initial_qty_raw = request.POST.get('initial_qty', '0').strip() or '0'

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not sku:
            errors['sku'] = 'SKU is required.'
        elif Product.objects.filter(sku=sku).exists():
            errors['sku'] = 'A product with this SKU already exists.'
        if not base_price:
            errors['base_price'] = 'Base price is required.'
        else:
            try:
                float(base_price)
            except ValueError:
                errors['base_price'] = 'Enter a valid price.'
        if not image:
            errors['image'] = 'Product image is required.'
        try:
            initial_qty = Decimal(initial_qty_raw)
            if initial_qty < 0:
                errors['initial_qty'] = 'Quantity cannot be negative.'
        except InvalidOperation:
            errors['initial_qty'] = 'Enter a valid quantity.'
            initial_qty = Decimal('0')

        if errors:
            ctx = {
                'categories': Category.objects.order_by('name'),
                'action': 'Create',
                'errors': errors,
                'values': _product_values(post=request.POST),
            }
            return render(request, self.template_name, ctx)

        product = Product.objects.create(
            name=name, sku=sku, base_price=base_price,
            category_id=category_id, description=description, is_active=is_active,
        )
        if image:
            product.image = image
            product.save(update_fields=['image'])

        # Create default variant + add to stock if quantity provided
        if initial_qty > 0:
            variant = ProductVariant.objects.create(
                product=product,
                sku=sku,
                is_active=True,
            )
            warehouse = Warehouse.objects.first()
            if warehouse:
                move = StockMove(
                    variant=variant,
                    warehouse=warehouse,
                    move_type=StockMove.MoveType.IN,
                    quantity=initial_qty,
                    reference=f'Initial stock — {product.name}',
                    created_by=request.user,
                )
                move.full_clean()
                move.save()
                sl, _ = StockLevel.objects.get_or_create(
                    variant=variant,
                    warehouse=warehouse,
                    defaults={'quantity': Decimal('0')},
                )
                sl.quantity = (sl.quantity or Decimal('0')) + initial_qty
                sl.save(update_fields=['quantity'])
            messages.success(request, f'Product "{product.name}" created with {int(initial_qty)} units in stock.')
        else:
            messages.success(request, f'Product "{product.name}" created.')

        return redirect('inventory:product-detail', pk=product.pk)


class ProductUpdateView(AdminRequiredMixin, View):
    template_name = 'inventory/product_form.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        ctx = {
            'categories': Category.objects.order_by('name'),
            'action': 'Edit',
            'product': product,
            'values': _product_values(product=product),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        name = request.POST.get('name', '').strip()
        sku = request.POST.get('sku', '').strip()
        base_price = request.POST.get('base_price', '').strip()
        category_id = request.POST.get('category') or None
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not sku:
            errors['sku'] = 'SKU is required.'
        elif Product.objects.filter(sku=sku).exclude(pk=pk).exists():
            errors['sku'] = 'A product with this SKU already exists.'
        if not base_price:
            errors['base_price'] = 'Base price is required.'
        else:
            try:
                float(base_price)
            except ValueError:
                errors['base_price'] = 'Enter a valid price.'

        if errors:
            ctx = {
                'categories': Category.objects.order_by('name'),
                'action': 'Edit',
                'product': product,
                'errors': errors,
                'values': _product_values(post=request.POST),
            }
            return render(request, self.template_name, ctx)

        product.name = name
        product.sku = sku
        product.base_price = base_price
        product.category_id = category_id
        product.description = description
        product.is_active = is_active
        if image:
            product.image = image
        product.save()

        messages.success(request, f'Product "{product.name}" updated.')
        return redirect('inventory:product-detail', pk=product.pk)


class ProductDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect('inventory:product-list')
