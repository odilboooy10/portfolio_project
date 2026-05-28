# ERP Core — Full Architecture Plan

## Current State (What Exists)

```
Internet
    ↓
Nginx (port 80)
    ↓
Gunicorn / Django
    ├── REST API  (/api/v1/)  — JWT auth, fully working
    ├── Frontend  (/dashboard/) — session auth, read-only KPIs
    └── Admin     (/admin/)    — Django built-in
         ↓
PostgreSQL ← Redis → Celery Worker
```

---

## Target Architecture

```
Internet
    ↓
Nginx
    ├── /static/  → served directly
    ├── /media/   → served directly
    └── /         → Gunicorn / Django
                       ├── REST API  (/api/v1/)     JWT auth
                       ├── Frontend  (/)            Session auth
                       │     ├── Auth      /login/ /logout/
                       │     ├── Dashboard /dashboard/
                       │     ├── Sales     /sales/
                       │     ├── CRM       /crm/
                       │     ├── Inventory /inventory/
                       │     ├── Purchase  /purchase/
                       │     ├── Accounting /accounting/
                       │     └── Users     /users/
                       └── Admin  (/admin/)
                            ↓
                       PostgreSQL
                            ↑
                       Redis → Celery Worker
                                 ├── send_payment_confirmation  (exists)
                                 ├── send_invoice_pdf_email     (Phase 1)
                                 └── dispatch_webhooks          (Phase 1)
```

---

## Frontend Architecture

### Template Hierarchy

```
templates/
├── base.html                       ← sidebar + topbar layout (EXISTS)
├── auth/
│   └── login.html                  ← (EXISTS)
├── _partials/                      ← HTMX fragments (Phase 2)
│   ├── flash_message.html
│   ├── confirm_modal.html
│   └── pagination.html
├── dashboard/
│   └── index.html                  ← (EXISTS)
├── sales/
│   ├── quotation_list.html
│   ├── quotation_form.html         ← create + edit
│   ├── quotation_detail.html
│   ├── order_list.html
│   ├── order_detail.html
│   ├── invoice_list.html
│   └── invoice_detail.html
├── crm/
│   ├── lead_list.html              ← table view
│   ├── lead_kanban.html            ← kanban board
│   ├── lead_form.html
│   └── lead_detail.html
├── inventory/
│   ├── product_list.html
│   ├── product_form.html
│   ├── stock_list.html
│   └── stock_move_form.html
├── purchase/
│   ├── vendor_list.html
│   ├── po_list.html
│   ├── po_form.html
│   ├── po_detail.html
│   └── receive_form.html
├── accounting/
│   ├── account_list.html
│   ├── entry_list.html
│   ├── entry_form.html
│   ├── entry_detail.html
│   └── payment_list.html
└── users/
    ├── user_list.html
    └── user_form.html
```

### URL Structure

```
/                               → redirect → /dashboard/
/login/   /logout/
/dashboard/

/sales/
    quotations/                 list
    quotations/create/          create form
    quotations/<id>/            detail
    quotations/<id>/edit/       edit form
    quotations/<id>/confirm/    HTMX action → creates order
    orders/                     list
    orders/<id>/                detail
    orders/<id>/invoice/        HTMX action → create invoice
    invoices/                   list
    invoices/<id>/              detail
    invoices/<id>/mark-paid/    HTMX action
    invoices/<id>/pdf/          PDF download (Phase 1)

/crm/
    leads/                      list (default)
    leads/kanban/               kanban board
    leads/create/
    leads/<id>/
    leads/<id>/edit/
    leads/<id>/won/             HTMX action
    leads/<id>/lost/            HTMX action
    leads/<id>/convert/         HTMX action

/inventory/
    products/
    products/create/
    products/<id>/
    products/<id>/edit/
    stock/                      stock levels table
    stock/adjust/               manual adjustment form
    moves/                      stock move log

/purchase/
    vendors/   vendors/create/   vendors/<id>/
    orders/    orders/create/    orders/<id>/
    orders/<id>/receive/         receive form

/accounting/
    accounts/  accounts/create/  accounts/<id>/
    entries/   entries/create/   entries/<id>/
    entries/<id>/post/           HTMX action
    entries/<id>/reverse/        HTMX action
    payments/  payments/create/

/users/
    /           list (admin only)
    create/
    <id>/edit/
```

### View Pattern Per Module

Each app gets:
- `frontend_views.py` — Django class-based views (ListView, DetailView, CreateView, UpdateView + action views)
- `frontend_forms.py` — Django ModelForms
- `urls_frontend.py` — URL config with `app_name` namespace

### HTMX Usage

| Interaction | HTMX pattern |
|---|---|
| Search / filter lists | `hx-get` + `hx-target="#table-body"` on input change |
| Status actions (confirm, post, mark-paid) | `hx-post` + `hx-target` replaces button/row |
| Inline validation | `hx-trigger="blur"` on form fields |
| Flash messages | `HX-Trigger` response header → toast injection |
| Confirm modal | `hx-confirm` attribute |

---

## Backend Additions (Option B)

### 1. Audit Log — `apps/audit`

```python
class AuditLog(models.Model):
    user         = FK(User)
    action       = CharField  # create | update | delete
    app_label    = CharField
    model_name   = CharField
    object_id    = CharField
    object_repr  = CharField  # str() of the object at time of action
    changes      = JSONField  # {"field": [before, after], ...}
    timestamp    = DateTimeField(auto_now_add=True)
```

**Implementation:** Django `post_save` / `post_delete` signals. An `AuditableMixin` added to all models enables tracking automatically. No middleware. Admin read-only view for the audit trail.

---

### 2. Role-Based Permission Matrix

```
                  Admin  Manager  Sales  Purchase  Accountant  Viewer
─────────────────────────────────────────────────────────────────────
Inventory  Read     ✅     ✅      ✅      ✅         ✅         ✅
Inventory  Write    ✅     ✅      ❌      ✅         ❌         ❌
Sales      Read     ✅     ✅      ✅      ❌         ✅         ✅
Sales      Write    ✅     ✅      ✅      ❌         ❌         ❌
CRM        Read     ✅     ✅      ✅      ❌         ❌         ✅
CRM        Write    ✅     ✅      ✅      ❌         ❌         ❌
Purchase   Read     ✅     ✅      ❌      ✅         ✅         ✅
Purchase   Write    ✅     ✅      ❌      ✅         ❌         ❌
Accounting Read     ✅     ✅      ❌      ❌         ✅         ❌
Accounting Write    ✅     ✅      ❌      ❌         ✅         ❌
Users      All      ✅     ❌      ❌      ❌         ❌         ❌
```

**Implementation:** `RolePermission` base class in `apps/users/permissions.py`. Applied via `RoleRequiredMixin` to frontend views and `RolePermission` to API views. Single source of truth.

---

### 3. PDF Invoice Export

- WeasyPrint (already installed) renders `templates/pdf/invoice.html`
- View: `GET /sales/invoices/<id>/pdf/` → `Content-Type: application/pdf`
- Celery task `send_invoice_pdf_email` attaches the PDF and emails the customer

---

### 4. API Rate Limiting

Library: `django-ratelimit`

| Endpoint group | Limit | Per |
|---|---|---|
| Auth (`/api/v1/auth/`) | 10 req/min | IP |
| Write endpoints (POST/PATCH/DELETE) | 60 req/min | User |
| Read endpoints (GET) | 300 req/min | User |

---

### 5. Webhook System — `apps/webhooks`

```python
class WebhookEndpoint(models.Model):
    url        = URLField
    events     = JSONField   # ["invoice.paid", "order.confirmed", ...]
    secret     = CharField   # HMAC-SHA256 signing key
    is_active  = BooleanField
    created_by = FK(User)

class WebhookDelivery(models.Model):
    endpoint        = FK(WebhookEndpoint)
    event           = CharField
    payload         = JSONField
    response_status = IntegerField(null=True)
    success         = BooleanField
    delivered_at    = DateTimeField
    error           = TextField(blank=True)
```

**Events fired:**
- `order.confirmed` — when a sale order is confirmed
- `invoice.paid` — when an invoice is marked paid
- `payment.created` — when a payment is recorded
- `lead.won` — when a CRM lead is marked won
- `po.received` — when a purchase order is fully received

**Implementation:** Django signals → Celery task `dispatch_webhooks(event, payload)` → POST to all active subscribed endpoints with `X-ERP-Signature: sha256=<hmac>` header.

---

## Implementation Order

### Phase 1 — Backend Hardening (Option B) ← START HERE

| Step | Task | Files |
|---|---|---|
| 1 | Audit log app | `apps/audit/models.py`, `signals.py`, `admin.py`, `mixins.py` |
| 2 | Role permission matrix | `apps/users/permissions.py` + update all app `permissions.py` |
| 3 | API rate limiting | `pip install django-ratelimit`, apply decorators |
| 4 | PDF invoice export | `templates/pdf/invoice.html`, view, Celery task |
| 5 | Webhook system | `apps/webhooks/` — models, signals, Celery task |

### Phase 2 — Frontend CRUD (Option A)

Build module by module in business-flow order:

| Step | Module | Key pages |
|---|---|---|
| 1 | Sales | Quotation list/create/detail, Order list/detail, Invoice list/detail/pdf |
| 2 | CRM | Lead list, Kanban board, Lead detail/form |
| 3 | Inventory | Product list/form, Stock levels, Stock move form |
| 4 | Purchase | Vendor list, PO list/create/detail, Receive form |
| 5 | Accounting | Account list, Journal entry list/form/detail, Payments |
| 6 | Users | User list, Create/edit form |

### Phase 3 — Polish

- Mobile responsive fixes
- Empty state illustrations when lists are empty
- Keyboard shortcuts
- Merge `develop` → `main` as stable release

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Frontend rendering | Server-side Django templates + HTMX | No duplicate logic, no SPA build step |
| Forms | Django ModelForms + crispy-bootstrap5 | Already installed, clean server-side validation |
| Inline actions | HTMX `hx-post` / `hx-target` | No full page reload, no JS framework |
| Audit log | Django signals | Non-intrusive, fires automatically on any model save/delete |
| Permissions | Role mixin on API + frontend views | Single source of truth, no duplication |
| PDF generation | WeasyPrint + HTML template | Already installed, CSS-driven, printable |
| Webhooks | Celery task + HMAC-SHA256 signing | Async, retryable, secure |
| Rate limiting | django-ratelimit | Lightweight, decorator-based, no infrastructure change |
