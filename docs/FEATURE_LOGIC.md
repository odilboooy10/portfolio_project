# Feature Logic Documentation

Who can do what, how it works, and why it works that way.

---

## Roles Overview

| Role | Who | Login Page | Landing Page |
|---|---|---|---|
| **Admin** | System owner / IT admin | `/login/` | `/dashboard/` |
| **Staff** | Company employees | `/login/` | `/dashboard/` |
| **Customer** | End customers (storefront) | `/store/login/` | `/store/catalog/` |

---

## ADMIN — Full Feature Logic

### 1. User Management

**What admin can do:**
- View all users (admin + staff + customers)
- See pending customer approvals (is_active=False, role='customer')
- Change any user's role (admin → staff or staff → admin)
- Activate / deactivate any user
- Cannot change their own role or deactivate themselves

**How it works:**
```
GET  /users/                    → UserListView   (AdminRequiredMixin)
GET  /users/<uuid>/             → UserDetailView (AdminRequiredMixin)
POST /users/<uuid>/change-role/ → UserChangeRoleView
POST /users/<uuid>/toggle-active/ → UserToggleActiveView
```

**Business logic:**
- `AdminRequiredMixin` checks `request.user.is_admin` → `role == 'admin'` or `is_superuser`
- Self-protection: if `user == request.user` → action blocked with error message
- Pending customers: `User.objects.filter(role='customer', is_active=False)` shown with "Pending" badge
- Activating a customer (`is_active=True`) allows them to log into the storefront

---

### 2. Dashboard

**What admin sees:**
- Revenue this month (sum of paid invoices)
- Active orders count
- Overdue invoices count
- Open leads count
- Monthly revenue chart (last 12 months)
- Top-selling products
- Low stock alerts
- Order pipeline by status
- Recent activity feed

**How it works:**
```
GET /dashboard/          → DashboardView (HTML)
GET /api/v1/dashboard/summary/       → revenue, orders, invoices KPIs
GET /api/v1/dashboard/revenue-chart/ → 12-month revenue data
GET /api/v1/dashboard/top-products/  → best sellers by quantity
GET /api/v1/dashboard/low-stock/     → variants below threshold
GET /api/v1/dashboard/activity/      → recent audit log entries
GET /api/v1/dashboard/pipeline/      → order counts by status
```

**Business logic:**
- All dashboard API endpoints require authentication (any role)
- Revenue = `Invoice.objects.filter(status='paid').aggregate(Sum('lines__unit_price * lines__quantity'))`
- Low stock threshold = quantity < 10 (configurable)
- Activity feed = last 20 AuditLog entries ordered by `created_at`

---

### 3. Sales — Full Control

**What admin can do:**
- View all customers, quotations, sale orders, invoices
- Create / edit / delete any record
- Confirm quotations → creates SaleOrder
- Mark invoices as paid
- Download PDF invoices
- Cancel orders

**How it works:**
```
GET  /sales/orders/              → OrderListView
GET  /sales/orders/<uuid>/       → OrderDetailView
GET  /sales/invoices/            → InvoiceListView
GET  /sales/invoices/<uuid>/     → InvoiceDetailView

POST /api/v1/sales/orders/<uuid>/confirm/   → status: draft → confirmed
POST /api/v1/sales/invoices/<uuid>/mark_paid/ → status: unpaid → paid
GET  /api/v1/sales/invoices/<uuid>/pdf/     → WeasyPrint PDF download
```

**Business logic — Order confirmation:**
```
Quotation (draft)
    ↓ confirm action
SaleOrder (confirmed)
    ↓ stock move created (OUT) for each line
StockLevel decremented per variant per warehouse
    ↓ invoice auto-linked
Invoice (unpaid) created with same lines
```

**Business logic — Invoice mark paid:**
```
Invoice (unpaid)
    ↓ mark_paid action
Invoice (paid) — paid_at = timezone.now()
    ↓ Celery task queued
Email sent to customer with PDF attachment
    ↓ Webhook fired (if configured)
POST to all active webhook endpoints
```

---

### 4. CRM — Full Control

**What admin can do:**
- View all leads in list and kanban board
- Create / edit / delete leads
- Assign leads to staff members
- Move leads between pipeline stages
- Mark leads as Won or Lost
- Log activities (calls, emails, meetings, notes)

**How it works:**
```
GET  /crm/leads/                 → LeadListView (filterable by pipeline, priority, state)
GET  /crm/kanban/                → KanbanView (grouped by Pipeline stage)
GET  /crm/leads/<uuid>/          → LeadDetailView
POST /crm/leads/<uuid>/win/      → LeadWinView  (sets won_at = now)
POST /crm/leads/<uuid>/lose/     → LeadLoseView (sets lost_at = now, stores reason)
POST /crm/leads/<uuid>/move-stage/ → LeadMoveStageView (changes pipeline FK)
```

**Business logic — Lead states:**
```
Lead.is_won  = property → won_at is not None
Lead.is_lost = property → lost_at is not None
Active lead  = won_at is None AND lost_at is None

Weighted revenue = expected_revenue × (probability / 100)
```

**Kanban query (N+1 safe):**
```python
Pipeline.objects.prefetch_related('leads__assigned_to').all()
# Column count: pipeline.leads.all()|length  (uses prefetch cache)
```

---

### 5. Inventory — Full Control

**What admin can do:**
- View all products, variants, stock levels
- Create / edit / delete products and variants
- View stock levels per warehouse
- Create stock moves (manual adjustments)
- View full stock move history

**How it works:**
```
GET  /inventory/products/        → ProductListView
GET  /inventory/products/<uuid>/ → ProductDetailView (with variants + stock)
GET  /inventory/stock/           → StockLevelView (all variants, all warehouses)
POST /inventory/stock-move/      → StockMoveCreateView (manual IN/OUT)
```

**Business logic — Stock ledger:**
```
Every stock change is recorded as a StockMove (append-only):
  move_type = 'in'  → stock received from supplier
  move_type = 'out' → stock shipped to customer
  move_type = 'adjustment' → manual correction

StockLevel.quantity = SUM(IN moves) - SUM(OUT moves) for that variant+warehouse
```

---

### 6. Purchase — Full Control

**What admin can do:**
- View all vendors and purchase orders
- Create / edit purchase orders
- Confirm RFQ → Purchase Order
- Receive goods → updates stock automatically
- View purchase history per vendor

**How it works:**
```
GET  /purchase/vendors/           → VendorListView
GET  /purchase/orders/            → POListView
GET  /purchase/orders/<uuid>/     → PODetailView
POST /api/v1/purchase/orders/<uuid>/confirm/ → status: rfq → confirmed
POST /api/v1/purchase/orders/<uuid>/receive/ → creates Receipt + StockMoves (IN)
```

**Business logic — Receive goods:**
```
PurchaseOrder (confirmed)
    ↓ receive action
Receipt created (linked to PO)
    ↓ for each line
ReceiptLine created (quantity_received set)
StockMove created (move_type='in', quantity=received_qty)
StockLevel incremented
PurchaseOrderLine.received_qty updated
If all lines fully received → PO status = 'received'
```

---

### 7. Accounting — Full Control

**What admin can do:**
- View Chart of Accounts (grouped by type)
- View / create / post journal entries
- View payments

**How it works:**
```
GET /accounting/accounts/         → AccountListView (grouped: asset/liability/income/expense)
GET /accounting/journals/         → JournalEntryListView
GET /accounting/journals/<uuid>/  → JournalEntryDetailView
GET /accounting/payments/         → PaymentListView

POST /api/v1/accounting/entries/<uuid>/post/ → status: draft → posted
```

**Business logic — Double-entry validation:**
```
JournalEntry is_balanced = SUM(debits) == SUM(credits)
Entry can only be posted if is_balanced = True
Posted entries cannot be edited (immutable)
```

---

## STAFF — Feature Logic

Staff has **identical access to all modules** as Admin except:

### What Staff CANNOT Do

| Feature | Why Blocked |
|---|---|
| `/users/` — view user list | `AdminRequiredMixin` → `user.is_admin` = False |
| `/users/<uuid>/` — view user detail | Same |
| Change any user's role | Same |
| Activate / deactivate users | Same |
| Approve pending customers | Same — only admin sees pending list |

### What Staff CAN Do (same as admin)

- Full Dashboard access
- Create / edit Sales orders, invoices, customers
- Create / edit CRM leads, move pipeline stages
- View + adjust Inventory
- Create / receive Purchase orders
- View + post Accounting journal entries
- Access API docs at `/api/v1/docs/`

### How Staff Restriction is Enforced

**Frontend:**
```python
# base.html sidebar
{% if request.user.is_admin %}
  <a href="/users/">Users</a>   ← only renders for admin
{% endif %}

# AdminRequiredMixin
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin  # False for staff → 403
```

**API:**
```python
# UsersPermission
class UsersPermission(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin')  # staff blocked at API level too
```

---

## CUSTOMER — Feature Logic

Customers are end users of the storefront. They have **zero access to the ERP**.

### 1. Sign Up

**What happens:**
```
Customer fills /store/signup/ form
    ↓
User created:
  role = 'customer'
  is_active = False   ← cannot log in yet
    ↓
Redirect to /store/pending/
  "Your account is pending admin approval"
    ↓
Admin sees "Pending" badge in /users/
Admin clicks user → Activate
  is_active = True
    ↓
Customer can now log in at /store/login/
```

**Business logic:**
- Email must be unique
- Password validated by Django's built-in validators
- `is_active=False` means Django's `authenticate()` returns None → login rejected

---

### 2. Login

**What happens:**
```
Customer submits /store/login/
    ↓
authenticate(email, password) called
    ↓
If is_active=False → "Your account is awaiting approval"
If role != 'customer' → "Use the staff login at /login/"
If credentials wrong → "Invalid email or password"
If all OK → login(request, user) → redirect /store/catalog/
```

**ERP login also protected:**
```
Staff submits /login/
    ↓
If role = 'customer' → "Customer accounts use /store/login/"
If all OK → redirect /dashboard/
```

---

### 3. Product Catalog

**What customer sees:**
- Grid of all active products with name, price, stock status
- Search by product name
- Filter by category
- "Add to Cart" button on each product

**How it works:**
```
GET /store/catalog/   → CatalogView (CustomerRequiredMixin)

Queryset:
Product.objects.filter(is_active=True)
    .prefetch_related('variants', 'category')
    .annotate(min_price=Min('variants__price_override'))
    .order_by('name')
```

**Stock status logic:**
```
StockLevel.objects.filter(variant__product=product).aggregate(Sum('quantity'))
> 0  → "In Stock"  (green)
= 0  → "Out of Stock" (red, Add to Cart disabled)
< 5  → "Low Stock" (yellow)
```

---

### 4. Add to Cart

**What happens:**
```
Customer clicks "Add to Cart" on a product
    ↓
POST /store/cart/add/  { variant_id, quantity=1 }
    ↓
Cart.objects.get_or_create(user=request.user)
    ↓
CartItem.objects.get_or_create(cart=cart, variant=variant)
  If new → quantity = 1
  If exists → UPDATE quantity = quantity + 1  (atomic F() expression)
    ↓
Redirect /store/cart/  with flash: "Laptop Pro added to cart"
```

**Constraints:**
- Cannot add out-of-stock items (button disabled in template)
- Cannot add more than available stock
- Cart is per-user — isolated with `cart__user=request.user`

---

### 5. Cart

**What customer sees:**
- Table: product name, SKU, unit price, quantity input, line total, remove button
- Order summary: subtotal, total
- "Proceed to Checkout" button
- Empty cart message if no items

**How it works:**
```
GET /store/cart/   → CartView

cart = Cart.objects.get_or_create(user=request.user)
items = cart.items.select_related('variant__product').all()
total = sum(item.variant.effective_price * item.quantity for item in items)
```

**Update quantity:**
```
POST /store/cart/update/  { item_id, quantity }
  If quantity = 0 → CartItem.delete()
  If quantity > 0 → CartItem.quantity = quantity
```

---

### 6. Checkout

**What happens:**
```
Customer fills checkout form (name, address, mock card)
    ↓
POST /store/checkout/
    ↓
1. Validate cart not empty
2. Check stock for every CartItem
   → if insufficient: show errors, abort
3. Get or create Customer record (sales.Customer) linked to this User
4. Wrap in transaction.atomic():
   a. Create SaleOrder (status='confirmed', customer=customer_record)
   b. Create SaleOrderLine per CartItem
   c. Create Invoice (status='paid')  ← mock payment always succeeds
   d. Create InvoiceLine per CartItem
   e. Create StockMove (OUT) per CartItem → decrements stock
   f. CartItem.objects.filter(cart=cart).delete()  ← clear cart
5. Redirect /store/orders/<order_id>/  (receipt page)
```

**Transaction safety:**
- All DB writes in `transaction.atomic()` — if any step fails, nothing is saved
- Customer sees error message if something goes wrong, cart is preserved

---

### 7. Order List

**What customer sees:**
- Their orders only — never another customer's orders
- Order reference, date, status badge, total
- Clickable rows → order detail

**How it works:**
```
GET /store/orders/   → OrderListView

queryset = SaleOrder.objects.filter(
    customer__user=request.user    ← ALWAYS scoped to this user
).select_related('customer').order_by('-confirmed_at')

paginate_by = 20
```

---

### 8. Order Detail + Receipt

**What customer sees:**
- Order reference, date, status
- Line items table: product, SKU, quantity, unit price, line total
- Order total
- Invoice status + paid date
- "Print Receipt" button → browser print dialog

**How it works:**
```
GET /store/orders/<uuid>/   → OrderDetailView

order = SaleOrder.objects.filter(
    pk=pk,
    customer__user=request.user   ← prevents accessing other customers' orders
).prefetch_related('lines__variant__product').first()

If order is None → 404  (not found OR belongs to someone else)
```

---

## Permission Enforcement Summary

| Action | Admin | Staff | Customer | Not Logged In |
|---|---|---|---|---|
| View Dashboard | ✅ | ✅ | ❌ → /store/login/ | ❌ → /login/ |
| View Sales Orders | ✅ | ✅ | ❌ | ❌ |
| Create Sale Order | ✅ | ✅ | ❌ | ❌ |
| View CRM Leads | ✅ | ✅ | ❌ | ❌ |
| View Inventory | ✅ | ✅ | ❌ | ❌ |
| View Accounting | ✅ | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ → 403 | ❌ | ❌ |
| View Catalog | ❌ → /dashboard/ | ❌ → /dashboard/ | ✅ | ❌ → /store/login/ |
| Add to Cart | ❌ | ❌ | ✅ | ❌ |
| Place Order | ❌ | ❌ | ✅ | ❌ |
| View Own Orders | ❌ | ❌ | ✅ | ❌ |
| View ALL Orders (ERP) | ✅ | ✅ | ❌ | ❌ |

---

## How Login Routing Works

```
User visits /login/
    ↓
Credentials valid?
    No  → "Invalid email or password"
    Yes → check role
        role = 'customer' → "Please use /store/login/"
        role = 'admin' or 'staff' → redirect /dashboard/

User visits /store/login/
    ↓
Credentials valid?
    No  → "Invalid email or password"
    Yes → check role + is_active
        role = 'admin'/'staff' → "Staff login is at /login/"
        is_active = False → "Your account is pending approval"
        role = 'customer' + is_active = True → redirect /store/catalog/
```

---

## Audit Trail

Every model change is automatically logged — admin and staff actions are recorded.

```
Who:    request.user (captured by signal)
What:   CREATE / UPDATE / DELETE
Which:  model name + object UUID
When:   timestamp
```

Stored in `AuditLog` table. Viewable at `/admin/audit/auditlog/`.

Triggered by `post_save` and `post_delete` signals on all models that inherit `AuditableMixin`.

---

## Security Layers

| Layer | How |
|---|---|
| Authentication | JWT tokens (API) + Django session (frontend) |
| Role enforcement | `AdminRequiredMixin`, `CustomerRequiredMixin`, DRF permission classes |
| Data isolation | Every queryset scoped to `request.user` |
| Rate limiting | `AuthRateThrottle` — 10/min unauthenticated, 100/min authenticated |
| HTTPS (production) | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| HSTS | `SECURE_HSTS_SECONDS = 31536000` |
| XSS protection | `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF` |
| Clickjacking | `X_FRAME_OPTIONS = 'DENY'` |
| CSRF | Django's built-in CSRF middleware (all POST forms) |
| SQL injection | Django ORM — no raw SQL |
