# Storefront — Edge Cases & Error Handling

All edge cases that can happen during the customer storefront flow, what the system does, and what the customer sees.

---

## 1. Sign Up

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Email already registered | `User.objects.filter(email=...).exists()` → form invalid | "An account with this email already exists." |
| Passwords do not match | Form validation fails | "Passwords do not match." |
| Password too short (< 8 chars) | Django password validator fails | "Password must be at least 8 characters." |
| Submits empty form | Required field validation | Field-level error messages |
| Signs up twice with same email | Blocked at form validation before DB hit | Same as above — "email already exists" |

---

## 2. Login

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Wrong email or password | `authenticate()` returns None | "Invalid email or password." |
| Account not yet approved (`is_active=False`) | Auth succeeds but login blocked | "Your account is pending admin approval. Please wait." |
| Admin/staff tries `/store/login/` | Role check fails | "Staff accounts use the main login at /login/" |
| Customer tries `/login/` (ERP) | Role check after auth | "Customer accounts use /store/login/" |
| Already logged in visits `/store/login/` | Redirect to `/store/catalog/` | Catalog page loads directly |
| Already logged in visits `/store/signup/` | Redirect to `/store/catalog/` | Catalog page loads directly |

---

## 3. Catalog

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| No products in DB | Empty queryset | "No products available yet." empty state |
| Product has no stock | `StockLevel` sum = 0 | "Out of Stock" badge, Add to Cart button disabled |
| Product has low stock (< 5) | `StockLevel` sum < 5 | "Low Stock" yellow badge, button still enabled |
| Product image missing | `product.image` is blank | Grey placeholder box with product icon |
| Search returns no results | Empty queryset | "No products match your search." |

---

## 4. Add to Cart

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Item already in cart | `get_or_create` returns existing → `UPDATE qty = qty + 1` | Flash: "Quantity updated in cart." |
| Out-of-stock item (direct POST bypass) | Stock check in view → abort | "This item is out of stock." flash error |
| Quantity would exceed stock | Stock check: `requested > available` | "Only X available in stock." |
| Not logged in | `CustomerRequiredMixin` redirects | Redirected to `/store/login/` |
| Invalid variant UUID | `get_object_or_404` → 404 | 404 page |

---

## 5. Cart

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Cart is empty | `cart.items.count() == 0` | "Your cart is empty." with link to catalog |
| Item removed manually from admin while in cart | CartItem still exists, variant exists | Cart shows item normally until next update |
| Variant deleted from system while in cart | `on_delete=CASCADE` on CartItem.variant | CartItem is deleted automatically, cart refreshes cleanly |
| Update quantity to 0 | `CartItem.delete()` | Item removed from cart, flash: "Item removed." |
| Update quantity to negative | Form validation min=1 | Field error: "Quantity must be at least 1." |
| Update quantity above stock | Stock check in UpdateCartView | "Only X in stock." flash error, quantity not updated |

---

## 6. Checkout

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Cart is empty at checkout | Early check → redirect | Redirected to `/store/cart/` with "Your cart is empty." |
| Stock runs out between Add to Cart and Checkout | Stock check at checkout time per item | "Laptop Pro: only 2 in stock, you requested 3." Error shown, order NOT created |
| Partial stock shortage (some items OK, some not) | All shortages collected → shown together | List of all stock errors, customer fixes cart and retries |
| Customer record already exists (returning customer) | `Customer.objects.get_or_create(email=...)` | Silently reuses existing Customer record |
| DB error during order creation | `transaction.atomic()` rolls back everything | "Something went wrong. Your cart has been preserved. Please try again." |
| Checkout form submitted empty | Required field validation | Field-level error messages, no order created |
| Double-click Place Order (duplicate submit) | Second request: cart already empty → redirect to orders | Lands on order list — only one order created |

---

## 7. Order List

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| No orders yet | Empty queryset | "You have no orders yet." with link to catalog |
| More than 20 orders | Paginated at 20/page | Pagination controls at bottom |
| Order was cancelled by admin | `status='cancelled'` shows in list | "Cancelled" red badge |

---

## 8. Order Detail

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Tries to access another customer's order URL | `filter(pk=pk, customer__email=request.user.email)` returns None | 404 page — no information leaked |
| Order UUID does not exist | Same queryset returns None | 404 page |
| Invoice not yet generated | `order.invoices.first()` is None | Order detail shows without invoice section |
| Prints receipt on unpaid order | Receipt renders but shows "Unpaid" status | Receipt with "Payment Pending" watermark status |

---

## 9. Admin Approval

| Edge Case | What Happens | Admin Sees |
|---|---|---|
| Admin activates already-active customer | `is_active` flips to True (no change) | "User activated." success message |
| Admin deactivates an active customer | `is_active=False` — customer immediately locked out | "User deactivated." |
| Deactivated customer tries to log in | `is_active=False` → blocked | "Your account is pending admin approval." |
| Admin tries to deactivate own account | `user == request.user` check → blocked | "You cannot deactivate your own account." |

---

## 10. Session & Auth

| Edge Case | What Happens | Customer Sees |
|---|---|---|
| Session expires mid-shopping | Cart preserved in DB (not session-based) | Redirected to `/store/login/`, cart intact after login |
| Customer logs out with items in cart | Cart stays in DB linked to user | Cart restored on next login |
| Customer uses two browsers simultaneously | Same DB cart, both see same state | Consistent cart across devices |
| CSRF token missing on form submit | Django CSRF middleware rejects | 403 Forbidden page |

---

## Error Handling Rules

### Flash Messages (user-facing)

| Type | CSS Class | When Used |
|---|---|---|
| Success | `alert-success` | Item added, order placed, quantity updated |
| Warning | `alert-warning` | Low stock notice, partial issue |
| Error | `alert-danger` | Out of stock, validation failed, DB error |
| Info | `alert-info` | Pending approval notice, informational |

### HTTP Status Codes

| Situation | Code |
|---|---|
| Page not found / no permission | 404 |
| Not authenticated | Redirect 302 to `/store/login/` |
| Wrong role (staff hits storefront) | Redirect 302 to `/dashboard/` |
| CSRF failure | 403 |
| Server error | 500 (Django default error page in dev) |

### Transaction Safety Rule

All checkout writes run inside `transaction.atomic()`:
- If **any** step fails → entire order rolled back → cart preserved → customer shown error
- If **all** steps succeed → cart cleared → customer redirected to order detail

### Stock Check Rule

Stock is checked **twice**:
1. At **Add to Cart** — prevents adding out-of-stock items
2. At **Checkout** — final check before order creation (stock may have changed)

This prevents overselling when multiple customers buy the last item simultaneously.
