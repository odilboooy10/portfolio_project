# Storefront — Build Plan

Customer-facing e-commerce layer on top of the existing ERP.

---

## Flow

```
/store/signup/    → customer registers (pending approval)
/store/login/     → customer logs in (only approved accounts)
/store/catalog/   → browse products
/store/cart/      → add / remove / update items
/store/checkout/  → enter details + mock payment
/store/orders/    → order history + receipt
```

---

## To-Do List

### Phase 1 — Backend

- [ ] **1.1** Add `customer` role to `User.Role` in `apps/users/models.py`
- [ ] **1.2** Create migration for new role
- [ ] **1.3** Create `apps/storefront/` app folder + `apps.py` + `__init__.py`
- [ ] **1.4** Create `apps/storefront/models.py` — `Cart`, `CartItem`
- [ ] **1.5** Register storefront in `INSTALLED_APPS` (`config/settings/base.py`)
- [ ] **1.6** Run `makemigrations` + `migrate`
- [ ] **1.7** Create `apps/storefront/admin.py`

### Phase 2 — Views

- [ ] **2.1** `CustomerSignupView` — creates User with `role='customer'`, `is_active=False`
- [ ] **2.2** `StoreLoginView` — authenticates customer, checks `role='customer'` + `is_active`
- [ ] **2.3** `PendingApprovalView` — shown after signup while waiting for admin
- [ ] **2.4** `CatalogView` — lists all active products with price + stock status
- [ ] **2.5** `ProductDetailView` — single product page with variants
- [ ] **2.6** `AddToCartView` — POST, adds variant to cart (creates Cart if first time)
- [ ] **2.7** `CartView` — shows cart items, quantities, totals, remove button
- [ ] **2.8** `CheckoutView` — GET: checkout form / POST: creates SaleOrder in ERP + clears cart
- [ ] **2.9** `OrderListView` — customer's order history
- [ ] **2.10** `OrderDetailView` — single order detail + printable receipt

### Phase 3 — URLs

- [ ] **3.1** Create `apps/storefront/urls.py` with all 10 routes
- [ ] **3.2** Register `/store/` in `config/urls.py`

### Phase 4 — Templates

- [ ] **4.1** `storefront/base.html` — clean header (Logo, Catalog, Cart badge, Orders, Logout) — no ERP sidebar
- [ ] **4.2** `storefront/signup.html` — registration form
- [ ] **4.3** `storefront/login.html` — customer login form
- [ ] **4.4** `storefront/pending.html` — "Your account is pending admin approval"
- [ ] **4.5** `storefront/catalog.html` — product grid with Add to Cart buttons
- [ ] **4.6** `storefront/product_detail.html` — product detail + variant selector
- [ ] **4.7** `storefront/cart.html` — cart table, quantities, total, Checkout button
- [ ] **4.8** `storefront/checkout.html` — name/address form + mock card fields
- [ ] **4.9** `storefront/order_list.html` — table of past orders with status badges
- [ ] **4.10** `storefront/order_detail.html` — order lines + total + printable receipt

### Phase 5 — Admin Approval

- [ ] **5.1** Update `templates/users/user_list.html` — show "Pending" badge for `is_active=False` customers
- [ ] **5.2** Update `UserListView` — add `pending_count` to context
- [ ] **5.3** Ensure "Activate" button on user detail page works for customer approval

### Phase 6 — Polish & Guards

- [ ] **6.1** `CustomerRequiredMixin` — blocks non-customers from storefront URLs
- [ ] **6.2** ERP login (`/login/`) rejects `role='customer'` users with clear message
- [ ] **6.3** Storefront login (`/store/login/`) rejects `role='admin'/'staff'` users
- [ ] **6.4** Cart item count shown in storefront header
- [ ] **6.5** Empty cart / no orders empty states
- [ ] **6.6** Run `manage.py check` — 0 issues
- [ ] **6.7** Test full flow end-to-end in browser

### Phase 7 — Commit & Push

- [ ] **7.1** Commit with message: `Add customer storefront — signup, catalog, cart, checkout, orders`
- [ ] **7.2** Push to `develop`

---

## Key Technical Decisions

| Decision | Choice |
|---|---|
| Cart storage | Database (Cart + CartItem models) |
| Payment | Mock — form submits, order marked paid immediately |
| Customer auth | Separate login page `/store/login/`, same User model with `role='customer'` |
| Order creation | Creates real `SaleOrder` + `Invoice` in ERP on checkout |
| Admin approval | Uses existing `is_active` toggle on User detail page |
| Storefront base | Completely separate template — no ERP sidebar |

---

## URL Map

| URL | View | Auth |
|---|---|---|
| `/store/signup/` | CustomerSignupView | Public |
| `/store/login/` | StoreLoginView | Public |
| `/store/pending/` | PendingApprovalView | Public |
| `/store/logout/` | StoreLogoutView | Customer |
| `/store/catalog/` | CatalogView | Customer |
| `/store/products/<uuid>/` | ProductDetailView | Customer |
| `/store/cart/` | CartView | Customer |
| `/store/cart/add/` | AddToCartView | Customer |
| `/store/cart/update/` | UpdateCartView | Customer |
| `/store/checkout/` | CheckoutView | Customer |
| `/store/orders/` | OrderListView | Customer |
| `/store/orders/<uuid>/` | OrderDetailView | Customer |
