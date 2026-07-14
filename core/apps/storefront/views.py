from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.inventory.models import Product, ProductVariant, StockLevel, StockMove, Warehouse
from apps.sales.models import Customer, Invoice, InvoiceLine, SaleOrder, SaleOrderLine
from apps.users.models import User

from .models import Cart, CartItem, ProductLike, ProductReview


class CustomerRequiredMixin(LoginRequiredMixin):
    login_url = '/store/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != User.Role.CUSTOMER:
            return redirect('dashboard:index')
        if not request.user.is_active:
            return redirect('store:pending')
        return super().dispatch(request, *args, **kwargs)


# ── Auth ──────────────────────────────────────────────────────────────────────

class CustomerSignupView(View):
    template_name = 'storefront/signup.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.role == User.Role.CUSTOMER:
            return redirect('store:catalog')
        return render(request, self.template_name)

    def post(self, request):
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = {}
        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'An account with this email already exists.'
        if not password1:
            errors['password1'] = 'Password is required.'
        elif len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters.'
        elif password1 != password2:
            errors['password2'] = 'Passwords do not match.'

        if errors:
            ctx = {'errors': errors, 'first_name': first_name, 'last_name': last_name, 'email': email}
            return render(request, self.template_name, ctx)

        username = email.split('@')[0] + '_' + str(User.objects.count())
        User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.CUSTOMER,
            is_active=False,
        )
        return redirect('store:pending')


class StoreLoginView(View):
    template_name = 'storefront/login.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.role == User.Role.CUSTOMER and request.user.is_active:
            return redirect('store:catalog')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, self.template_name, {'error': 'Invalid email or password.'})

        if user_obj.role != User.Role.CUSTOMER:
            return render(request, self.template_name, {
                'error': 'Staff accounts use the main login at /login/'
            })

        user = authenticate(request, username=user_obj.email, password=password)
        if user is None:
            if not user_obj.is_active:
                return render(request, self.template_name, {
                    'error': 'Your account is pending admin approval. Please wait.'
                })
            return render(request, self.template_name, {'error': 'Invalid email or password.'})

        if not user.is_active:
            return render(request, self.template_name, {
                'error': 'Your account is pending admin approval. Please wait.'
            })

        login(request, user)
        return redirect('store:catalog')


class StoreLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('store:login')

    def get(self, request):
        logout(request)
        return redirect('store:login')


class PendingApprovalView(View):
    template_name = 'storefront/pending.html'

    def get(self, request):
        return render(request, self.template_name)


# ── Catalog ───────────────────────────────────────────────────────────────────

class CatalogView(CustomerRequiredMixin, View):
    template_name = 'storefront/catalog.html'

    def get(self, request):
        qs = Product.objects.filter(is_active=True).prefetch_related(
            'variants', 'category'
        ).annotate(
            like_count=Count('likes', distinct=True),
            avg_rating=Avg('reviews__rating'),
        ).order_by('name')

        q = request.GET.get('q', '').strip()
        category_id = request.GET.get('category', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        if category_id:
            qs = qs.filter(category_id=category_id)

        from apps.inventory.models import Category
        categories = Category.objects.order_by('name')

        products_data = []
        for product in qs:
            total_stock = StockLevel.objects.filter(
                variant__product=product
            ).aggregate(total=Sum('quantity'))['total'] or 0

            first_variant = product.variants.filter(is_active=True).first()
            avg = product.avg_rating
            products_data.append({
                'product': product,
                'total_stock': total_stock,
                'first_variant': first_variant,
                'like_count': product.like_count,
                'avg_rating': round(avg, 1) if avg else None,
                'avg_rating_rounded': round(avg) if avg else 0,
            })

        ctx = {
            'products_data': products_data,
            'q': q,
            'categories': categories,
            'current_category': category_id,
        }
        return render(request, self.template_name, ctx)


class ProductDetailView(CustomerRequiredMixin, View):
    template_name = 'storefront/product_detail.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)
        variants = product.variants.filter(is_active=True).prefetch_related('attribute_values')

        variants_data = []
        for v in variants:
            stock = StockLevel.objects.filter(variant=v).aggregate(total=Sum('quantity'))['total'] or 0
            variants_data.append({'variant': v, 'stock': stock})

        reviews = product.reviews.select_related('user').all()
        avg = reviews.aggregate(avg=Avg('rating'))['avg']
        user_review = product.reviews.filter(user=request.user).first()
        like_count = product.likes.count()
        user_liked = product.likes.filter(user=request.user).exists()

        can_review = SaleOrder.objects.filter(
            customer__email=request.user.email,
            status=SaleOrder.Status.DONE,
            lines__variant__product=product,
        ).exists()

        ctx = {
            'product': product,
            'variants_data': variants_data,
            'reviews': reviews,
            'avg_rating': round(avg, 1) if avg else None,
            'avg_rating_rounded': round(avg) if avg else 0,
            'review_count': reviews.count(),
            'user_review': user_review,
            'like_count': like_count,
            'user_liked': user_liked,
            'can_review': can_review,
        }
        return render(request, self.template_name, ctx)


# ── Cart ──────────────────────────────────────────────────────────────────────

class AddToCartView(CustomerRequiredMixin, View):
    def post(self, request):
        variant_id = request.POST.get('variant_id')
        variant = get_object_or_404(ProductVariant, pk=variant_id, is_active=True)

        stock = StockLevel.objects.filter(variant=variant).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        if stock <= 0:
            messages.error(request, 'This item is out of stock.')
            return redirect('store:catalog')

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        if not created:
            if item.quantity + 1 > stock:
                messages.warning(request, f'Only {int(stock)} available in stock.')
            else:
                item.quantity = F('quantity') + 1
                item.save(update_fields=['quantity'])
                messages.success(request, f'{variant.product.name} quantity updated in cart.')
        else:
            messages.success(request, f'{variant.product.name} added to cart.')

        return redirect('store:cart')


class CartView(CustomerRequiredMixin, View):
    template_name = 'storefront/cart.html'

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related('variant__product').all()
        total = sum(item.line_total for item in items)
        ctx = {'cart': cart, 'items': items, 'total': total}
        return render(request, self.template_name, ctx)


class UpdateCartView(CustomerRequiredMixin, View):
    def post(self, request):
        item_id = request.POST.get('item_id')
        item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)

        try:
            qty = int(request.POST.get('quantity', 0))
        except (ValueError, TypeError):
            qty = 0

        if qty <= 0:
            item.delete()
            messages.success(request, 'Item removed from cart.')
        else:
            stock = StockLevel.objects.filter(variant=item.variant).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            if qty > stock:
                messages.warning(request, f'Only {int(stock)} in stock.')
            else:
                item.quantity = qty
                item.save(update_fields=['quantity'])

        return redirect('store:cart')


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutView(CustomerRequiredMixin, View):
    template_name = 'storefront/checkout.html'

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related('variant__product').all()
        if not items.exists():
            messages.warning(request, 'Your cart is empty.')
            return redirect('store:cart')
        total = sum(item.line_total for item in items)
        ctx = {
            'cart': cart,
            'items': items,
            'total': total,
            'user': request.user,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = list(cart.items.select_related('variant__product').all())

        if not items:
            messages.warning(request, 'Your cart is empty.')
            return redirect('store:cart')

        # Stock check
        stock_errors = []
        for item in items:
            available = StockLevel.objects.filter(variant=item.variant).aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')
            if item.quantity > available:
                stock_errors.append(
                    f'{item.variant.product.name}: only {int(available)} in stock, you requested {item.quantity}.'
                )

        if stock_errors:
            for err in stock_errors:
                messages.error(request, err)
            total = sum(item.line_total for item in items)
            return render(request, self.template_name, {
                'cart': cart, 'items': items, 'total': total, 'user': request.user
            })

        # Get shipping info
        shipping_address = request.POST.get('address', '').strip()
        warehouse = Warehouse.objects.first()

        try:
            with transaction.atomic():
                # Get or create sales Customer record
                customer_rec, _ = Customer.objects.get_or_create(
                    email=request.user.email,
                    defaults={
                        'name': request.user.full_name or request.user.email,
                        'address': shipping_address,
                    }
                )
                if shipping_address and customer_rec.address != shipping_address:
                    customer_rec.address = shipping_address
                    customer_rec.save(update_fields=['address'])

                # Create SaleOrder
                order = SaleOrder.objects.create(
                    customer=customer_rec,
                    status=SaleOrder.Status.CONFIRMED,
                    note=f'Storefront order — {request.user.email}',
                )

                # Create Invoice
                now = timezone.now()
                invoice = Invoice.objects.create(
                    sale_order=order,
                    customer=customer_rec,
                    status=Invoice.Status.PAID,
                    issue_date=now.date(),
                    due_date=now.date(),
                    paid_at=now,
                    note='Paid via storefront checkout',
                )

                for item in items:
                    price = item.variant.effective_price
                    qty = Decimal(str(item.quantity))

                    SaleOrderLine.objects.create(
                        order=order,
                        variant=item.variant,
                        quantity=qty,
                        unit_price=price,
                    )
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        variant=item.variant,
                        quantity=qty,
                        unit_price=price,
                    )

                    if warehouse:
                        move = StockMove(
                            variant=item.variant,
                            warehouse=warehouse,
                            move_type=StockMove.MoveType.OUT,
                            quantity=-qty,
                            reference=order.reference,
                            note=f'Storefront order {order.reference}',
                        )
                        move.full_clean()
                        move.save()

                        sl, _ = StockLevel.objects.get_or_create(
                            variant=item.variant,
                            warehouse=warehouse,
                            defaults={'quantity': Decimal('0')},
                        )
                        sl.quantity = (sl.quantity or Decimal('0')) - qty
                        sl.save(update_fields=['quantity'])

                cart.items.all().delete()

        except Exception:
            messages.error(
                request,
                'Something went wrong. Your cart has been preserved. Please try again.'
            )
            return redirect('store:checkout')

        return redirect('store:order-detail', pk=order.pk)


# ── Orders ────────────────────────────────────────────────────────────────────

class OrderListView(CustomerRequiredMixin, View):
    template_name = 'storefront/order_list.html'

    def get(self, request):
        qs = SaleOrder.objects.filter(
            customer__email=request.user.email
        ).select_related('customer').order_by('-confirmed_at')

        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get('page'))
        ctx = {'page_obj': page, 'orders': page.object_list}
        return render(request, self.template_name, ctx)


class OrderDetailView(CustomerRequiredMixin, View):
    template_name = 'storefront/order_detail.html'

    def get(self, request, pk):
        order = SaleOrder.objects.filter(
            pk=pk,
            customer__email=request.user.email,
        ).prefetch_related('lines__variant__product').first()

        if order is None:
            from django.http import Http404
            raise Http404

        invoice = order.invoices.first()
        total = sum(line.line_total for line in order.lines.all())
        ctx = {'order': order, 'invoice': invoice, 'total': total}
        return render(request, self.template_name, ctx)


# ── Likes & Reviews ───────────────────────────────────────────────────────────

class LikeToggleView(CustomerRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)
        like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
        if not created:
            like.delete()
        return redirect('store:product-detail', pk=pk)


class ReviewCreateView(CustomerRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)

        can_review = SaleOrder.objects.filter(
            customer__email=request.user.email,
            status=SaleOrder.Status.DONE,
            lines__variant__product=product,
        ).exists()

        if not can_review:
            messages.error(request, 'You can only review a product after it has been delivered.')
            return redirect('store:product-detail', pk=pk)

        rating_raw = request.POST.get('rating', '').strip()
        body = request.POST.get('body', '').strip()

        try:
            rating = int(rating_raw)
            if not 1 <= rating <= 5:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Please select a rating between 1 and 5.')
            return redirect('store:product-detail', pk=pk)

        if not body:
            messages.error(request, 'Review text is required.')
            return redirect('store:product-detail', pk=pk)

        _, created = ProductReview.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'rating': rating, 'body': body},
        )
        messages.success(request, 'Review submitted.' if created else 'Review updated.')
        return redirect('store:product-detail', pk=pk)
