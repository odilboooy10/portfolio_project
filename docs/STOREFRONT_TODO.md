# Storefront — To-Do List

Customer-facing storefront build tracker. Check off each task as it is completed.

---

## Phase 1 — Backend

- [ ] 1.1 Add `customer` role to `User.Role` in `apps/users/models.py`
- [ ] 1.2 Create migration for new role
- [ ] 1.3 Create `apps/storefront/` app folder (`__init__.py`, `apps.py`)
- [ ] 1.4 Create `apps/storefront/models.py` — `Cart`, `CartItem`
- [ ] 1.5 Add `apps.storefront` to `INSTALLED_APPS` in `config/settings/base.py`
- [ ] 1.6 Run `makemigrations storefront` + `migrate`
- [ ] 1.7 Create `apps/storefront/admin.py`

## Phase 2 — Views

- [ ] 2.1 `CustomerSignupView` — creates User with `role='customer'`, `is_active=False`
- [ ] 2.2 `StoreLoginView` — authenticates customer, checks role + is_active
- [ ] 2.3 `StoreLogoutView` — logs out customer, redirects to `/store/login/`
- [ ] 2.4 `PendingApprovalView` — shown after signup while waiting for admin
- [ ] 2.5 `CatalogView` — lists all active products with price + stock status
- [ ] 2.6 `ProductDetailView` — single product page with variants
- [ ] 2.7 `AddToCartView` — POST, adds variant to cart atomically
- [ ] 2.8 `CartView` — shows cart items, quantities, totals, remove button
- [ ] 2.9 `UpdateCartView` — POST, updates quantity or removes item
- [ ] 2.10 `CheckoutView` — GET: form / POST: creates SaleOrder + Invoice + clears cart
- [ ] 2.11 `OrderListView` — customer's own order history (scoped by email)
- [ ] 2.12 `OrderDetailView` — single order detail + printable receipt

## Phase 3 — URLs

- [ ] 3.1 Create `apps/storefront/urls.py` with all 12 routes
- [ ] 3.2 Register `path('store/', ...)` in `config/urls.py`

## Phase 4 — Templates

- [ ] 4.1 `storefront/base.html` — clean top-nav (Logo, Catalog, Cart badge, Orders, Logout)
- [ ] 4.2 `storefront/signup.html` — registration form (name, email, password)
- [ ] 4.3 `storefront/login.html` — customer login form
- [ ] 4.4 `storefront/pending.html` — "Your account is pending admin approval"
- [ ] 4.5 `storefront/catalog.html` — product grid with Add to Cart buttons
- [ ] 4.6 `storefront/product_detail.html` — product detail + variant selector
- [ ] 4.7 `storefront/cart.html` — cart table, quantities, total, Checkout button
- [ ] 4.8 `storefront/checkout.html` — address form + mock card fields
- [ ] 4.9 `storefront/order_list.html` — table of past orders with status badges
- [ ] 4.10 `storefront/order_detail.html` — order lines + total + printable receipt

## Phase 5 — Admin Approval

- [ ] 5.1 Update `templates/users/user_list.html` — show "Pending" badge for unapproved customers
- [ ] 5.2 Update `UserListView.get_context_data` — add `pending_count` to context

## Phase 6 — Guards & Routing

- [ ] 6.1 `CustomerRequiredMixin` — redirects non-customers away from storefront
- [ ] 6.2 ERP `/login/` rejects `role='customer'` with message "Use /store/login/"
- [ ] 6.3 Store `/store/login/` rejects staff/admin with message "Use /login/"
- [ ] 6.4 Cart item count shown in storefront header on every page
- [ ] 6.5 Empty states — empty cart, no orders, no products messages

## Phase 7 — Commit & Push

- [ ] 7.1 Run `manage.py check` — 0 issues
- [ ] 7.2 Run full test suite — 0 failures
- [ ] 7.3 Test full flow in browser end-to-end
- [ ] 7.4 Commit: `Add customer storefront — signup, catalog, cart, checkout, orders`
- [ ] 7.5 Push to `develop`

---

## Progress

| Phase | Tasks | Done |
|---|---|---|
| Phase 1 — Backend | 7 | 0 |
| Phase 2 — Views | 12 | 0 |
| Phase 3 — URLs | 2 | 0 |
| Phase 4 — Templates | 10 | 0 |
| Phase 5 — Admin Approval | 2 | 0 |
| Phase 6 — Guards | 5 | 0 |
| Phase 7 — Commit & Push | 5 | 0 |
| **Total** | **43** | **0** |
