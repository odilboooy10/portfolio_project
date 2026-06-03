# Storefront — Technical Documentation

How the system handles multiple users, multiple carts, and multiple order lists safely and efficiently.

---

## 1. User Isolation — How Each Customer Sees Only Their Own Data

Every piece of customer data is **anchored to the User ID**. No customer can see another's cart or orders.

### Cart

```
User (id=A)  ──OneToOne──►  Cart (id=1)  ──►  CartItem (variant=Laptop, qty=2)
                                          ──►  CartItem (variant=Mouse, qty=1)

User (id=B)  ──OneToOne──►  Cart (id=2)  ──►  CartItem (variant=Chair, qty=3)
```

- One cart per user — enforced by `OneToOneField`
- Cart is created automatically on first "Add to Cart"
- `Cart.objects.get(user=request.user)` — always returns only that user's cart

### Orders

```
User (id=A)  ──►  Customer record (email=a@example.com)
                       ──►  SaleOrder #SO-0001  (TechCorp, $2,575)
                       ──►  SaleOrder #SO-0004  (TechCorp, $899)

User (id=B)  ──►  Customer record (email=b@example.com)
                       ──►  SaleOrder #SO-0002  (Global Inc, $897)
```

- Orders are filtered by `customer__user=request.user` in every view
- A customer can never see another's orders — the queryset is scoped at the view level

### Code Pattern (applied to every storefront view)

```python
class OrderListView(CustomerRequiredMixin, ListView):
    def get_queryset(self):
        # ALWAYS scope to the logged-in customer — never show all orders
        return SaleOrder.objects.filter(
            customer__user=self.request.user
        ).order_by('-confirmed_at')
```

---

## 2. Database Relationships

```
User
 │
 ├── role = 'customer'
 ├── is_active = True/False (False = pending approval)
 │
 ├──OneToOne──► Cart
 │                └──FK──► CartItem (variant, quantity)
 │                              └──FK──► ProductVariant
 │
 └──FK──► Customer (sales app)
               └──FK──► SaleOrder
                              ├──FK──► SaleOrderLine (variant, qty, price)
                              └──FK──► Invoice
                                           └──FK──► InvoiceLine
```

---

## 3. Handling Many Users + Many Orders

### 3.1 Pagination

Order lists are paginated — no full table scans shown to the user.

```python
class OrderListView(CustomerRequiredMixin, ListView):
    paginate_by = 20  # show 20 orders per page
    
    def get_queryset(self):
        return SaleOrder.objects.filter(
            customer__user=self.request.user
        ).select_related('customer').order_by('-confirmed_at')
```

URL pattern: `/store/orders/?page=2`

### 3.2 Database Indexes

Key fields that get queried on every request are indexed:

| Table | Indexed Field | Why |
|---|---|---|
| `users_user` | `email` | Login lookup |
| `users_user` | `role`, `is_active` | Admin filtering pending customers |
| `storefront_cart` | `user_id` | Cart lookup on every page load |
| `storefront_cartitem` | `cart_id` | Cart items query |
| `sales_saleorder` | `customer_id` | Order list per customer |
| `sales_invoice` | `sale_order_id` | Invoice lookup from order |

### 3.3 Efficient Queries (N+1 Prevention)

Without optimization, loading 20 orders hits the DB 40+ times.
With `select_related` / `prefetch_related`, it stays at 3-4 queries regardless of order count.

```python
# Order list — 2 queries total
SaleOrder.objects.filter(
    customer__user=request.user
).select_related('customer')

# Order detail — 3 queries total  
SaleOrder.objects.filter(
    pk=pk, customer__user=request.user
).select_related('customer').prefetch_related(
    'lines__variant__product'
)
```

---

## 4. Cart Concurrency — Race Conditions

When a user rapidly clicks "Add to Cart," two requests may try to create the same CartItem simultaneously.

**Problem:**
```
Request 1: CartItem does not exist → creating...
Request 2: CartItem does not exist → creating...
Request 1: INSERT CartItem (variant=Laptop, qty=1) ✅
Request 2: INSERT CartItem (variant=Laptop, qty=1) → IntegrityError ❌
```

**Solution — `get_or_create` + atomic update:**

```python
def add_to_cart(request, variant_id):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    variant = get_object_or_404(ProductVariant, pk=variant_id)

    # Atomic: get existing or create new, then increment
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={'quantity': 1}
    )
    if not created:
        # Already in cart — increment quantity atomically
        CartItem.objects.filter(pk=item.pk).update(
            quantity=F('quantity') + 1
        )
```

`F('quantity') + 1` is a single SQL `UPDATE quantity = quantity + 1` — safe under concurrent requests.

---

## 5. Stock Check at Checkout

Before creating the order, verify stock is available for every item.

```python
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    errors = []

    for item in cart.items.select_related('variant'):
        stock = StockLevel.objects.filter(
            variant=item.variant
        ).aggregate(total=Sum('quantity'))['total'] or 0

        if stock < item.quantity:
            errors.append(
                f"{item.variant.product.name}: only {stock} in stock, you requested {item.quantity}"
            )

    if errors:
        # Show errors, do not create order
        return render(request, 'storefront/checkout.html', {'errors': errors})

    # Stock OK — create order
    ...
```

---

## 6. Admin Approval Flow

```
Customer signs up
      ↓
User created: role='customer', is_active=False
      ↓
Admin opens /users/ — sees "Pending" badge on unapproved customers
      ↓
Admin clicks user → User Detail page
      ↓
Admin clicks "Activate" button
      ↓
is_active=True — customer can now log in
```

### Pending customers visible to admin

```python
# UserListView context
ctx['pending_count'] = User.objects.filter(
    role='customer', is_active=False
).count()
```

The Users list will show a **"3 Pending Approval"** banner at the top when there are customers waiting.

---

## 7. Login Routing — Who Goes Where

```
/login/         → ERP login (admin + staff only)
                  If role='customer' → rejected with message "Use /store/login/"

/store/login/   → Storefront login (customers only)
                  If role='admin'/'staff' → rejected with "Use /login/"
                  If is_active=False → "Your account is pending approval"
```

After login:
- `admin` / `staff` → `/dashboard/`
- `customer` → `/store/catalog/`

---

## 8. Order States — What Customer Sees

| ERP Status | Customer Label | Meaning |
|---|---|---|
| `confirmed` | Order Placed | Order received |
| `confirmed` + invoice `unpaid` | Awaiting Payment | Payment pending |
| `confirmed` + invoice `paid` | Paid | Payment confirmed |
| `cancelled` | Cancelled | Order was cancelled |

Receipt is available once invoice status is `paid`.

---

## 9. Full Request Flow — Add to Cart

```
Customer clicks "Add to Cart" on Laptop
        ↓
POST /store/cart/add/  { variant_id: "uuid", quantity: 1 }
        ↓
View: CustomerRequiredMixin → checks role='customer' + is_active=True
        ↓
Cart.objects.get_or_create(user=request.user)
        ↓
CartItem.objects.get_or_create(cart=cart, variant=variant)
        ↓
If exists: UPDATE quantity = quantity + 1  (atomic)
        ↓
Redirect → /store/cart/  with success message "Laptop added to cart"
```

---

## 10. Full Request Flow — Checkout

```
Customer clicks "Place Order"
        ↓
POST /store/checkout/  { name, address, card_number (mock) }
        ↓
1. Validate cart is not empty
2. Check stock for every item
3. Get or create Customer record (sales app) linked to this User
4. Create SaleOrder (status='confirmed')
5. Create SaleOrderLine for each CartItem
6. Create Invoice (status='paid') — mock payment always succeeds
7. Create InvoiceLine for each line
8. Clear CartItems
9. Redirect → /store/orders/<order_id>/  (receipt page)
```

All steps 4–8 run inside a **database transaction** — if any step fails, everything rolls back and no partial order is created.

```python
from django.db import transaction

with transaction.atomic():
    order = SaleOrder.objects.create(...)
    for item in cart_items:
        SaleOrderLine.objects.create(order=order, ...)
    invoice = Invoice.objects.create(order=order, status='paid', ...)
    cart.items.all().delete()
```
