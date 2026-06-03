# ERP Core — Django ERP Suite (Portfolio Project)

A full-featured ERP / business management system built with Django, inspired by Odoo Community Edition.
Built as a portfolio project to demonstrate backend Python / fullstack development skills.

---

## Project Goal

Build a production-grade ERP suite modular enough to impress in job interviews.
The idea: study Odoo's business logic and patterns, then reimplement them cleanly in Django.
Not a copy — our own architecture, our own code, Odoo as the domain reference.

**Target roles:** Backend Python developer, Fullstack developer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt) + Djoser |
| API Docs | drf-spectacular (OpenAPI 3 / Swagger) |
| Frontend | HTMX + Alpine.js + Bootstrap 5 (Django templates, no SPA) |
| Database | PostgreSQL 15 |
| Async | Celery + Redis |
| Task scheduling | django-celery-beat |
| PDF generation | WeasyPrint |
| Forms | django-crispy-forms + crispy-bootstrap5 |
| Dev tools | django-debug-toolbar, django-extensions, pytest-django, factory-boy |
| Deploy | Docker + Nginx + Gunicorn + GitHub Actions CI |

---

## Current Project Structure

```
portfolio-project/
├── .env                        ← local env vars (never commit this)
├── .env.example                ← template for env vars (commit this)
├── .gitignore
├── README.md                   ← you are here
├── requirements/
│   ├── base.txt                ← shared dependencies
│   ├── local.txt               ← base + dev tools (debug toolbar, pytest, etc.)
│   └── production.txt          ← base + gunicorn
├── venv/                       ← Python 3.11 virtual environment (gitignored)
├── nginx/                      ← nginx config (to be added)
├── docker-compose.yml          ← to be added
└── core/                       ← Django project root
    ├── manage.py
    ├── config/                 ← project-level configuration
    │   ├── settings/
    │   │   ├── __init__.py
    │   │   ├── base.py         ← all shared settings
    │   │   ├── local.py        ← DEBUG=True, debug toolbar
    │   │   └── production.py   ← security headers, DEBUG=False
    │   ├── urls.py             ← root URL conf (admin + debug toolbar)
    │   ├── api_urls.py         ← /api/v1/ routes (auth, docs, future modules)
    │   ├── celery.py           ← Celery app (to be added)
    │   ├── wsgi.py
    │   └── asgi.py
    ├── apps/                   ← all business logic lives here
    │   ├── users/              ✅ DONE — custom User model
    │   ├── inventory/          🔲 NEXT — products, variants, stock
    │   ├── sales/              🔲 TODO — orders, invoices, customers
    │   ├── crm/                🔲 TODO — leads, pipeline, activities
    │   ├── purchase/           🔲 TODO — vendors, purchase orders
    │   ├── accounting/         🔲 TODO — payments, journals, reports
    │   └── dashboard/          🔲 TODO — analytics, KPIs, charts
    ├── templates/              ← global HTML templates (base layout, partials)
    ├── static/                 ← global CSS, JS, images
    └── media/                  ← user-uploaded files (gitignored)
```

---

## What Has Been Built

### ✅ Project Scaffold
- Django project created with **split settings** (base / local / production)
- `django-environ` for all secrets via `.env` file — no hardcoded credentials
- PostgreSQL configured as the database
- All 7 app modules scaffolded under `core/apps/`

### ✅ Custom User Model (`apps/users`)
**This must always be set up before the first migration — it was.**

```python
# Key design decisions:
AUTH_USER_MODEL = 'users.User'   # in settings
```

Features:
- UUID primary key (not sequential int — better for APIs and security)
- Email as login field (`USERNAME_FIELD = 'email'`)
- Role-based access with `TextChoices`: `admin`, `manager`, `sales`, `purchase`, `accountant`, `viewer`
- Extra fields: `phone`, `avatar`, `is_verified`
- Properties: `full_name`, `is_admin`, `is_manager`
- Registered in Django admin with custom `UserAdmin`

### ✅ REST API Foundation
- DRF configured with JWT authentication
- Djoser handling user registration / login / password reset
- drf-spectacular generating OpenAPI 3 schema
- Swagger UI live at `/api/v1/docs/`
- Redoc live at `/api/v1/redoc/`

### ✅ Database
- PostgreSQL database `erp_core` created locally
- User `erp_user` with full privileges
- All initial migrations applied (Django core + celery-beat + celery-results + users)

### ✅ Dev Tooling
- `django-debug-toolbar` wired up for local development
- `pytest-django`, `factory-boy` installed for testing
- `django-extensions` for shell_plus, graph_models, etc.

---

## Running Locally

### Prerequisites
- Python 3.11 (`/opt/homebrew/bin/python3.11`)
- PostgreSQL 15 running (`brew services start postgresql@15`)
- Redis running (`brew services start redis`)

### Start the server
```bash
# From portfolio-project/
source venv/bin/activate
cd core
python manage.py runserver
```

### Useful URLs (local)
| URL | What |
|---|---|
| http://127.0.0.1:8000/admin/ | Django admin |
| http://127.0.0.1:8000/api/v1/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/v1/redoc/ | Redoc |
| http://127.0.0.1:8000/__debug__/ | Debug toolbar |

### Admin credentials (local only)
- Email: `admin@erp.local`
- Password: `admin123`

### Environment variables
Copy `.env.example` to `.env` and fill in values.
The `.env` file must sit in `portfolio-project/` (one level above `core/`).

---

## Modules — Build Plan

### 🔲 Next: Inventory (`apps/inventory`)
Inspired by Odoo's `product` + `stock` modules.

Models to build:
- `Category` — hierarchical product categories (parent/child)
- `Product` — base product (name, description, SKU, price, images)
- `ProductAttribute` — e.g. "Size", "Color"
- `ProductVariant` — specific combination: Product + Attributes (e.g. T-Shirt / Red / XL)
- `Warehouse` — physical storage locations
- `StockMove` — every inventory movement (in/out/transfer) — append-only ledger pattern
- `StockLevel` — current quantity per variant per warehouse (computed from StockMove)

API endpoints:
- `GET /api/v1/inventory/products/` — list/search products
- `POST /api/v1/inventory/products/` — create product (admin/manager only)
- `GET /api/v1/inventory/products/{id}/` — product detail with variants and stock
- `POST /api/v1/inventory/stock/adjust/` — manual stock adjustment

---

### 🔲 Sales (`apps/sales`)
Inspired by Odoo's `sale` module.

Models: `Customer`, `Quotation`, `SaleOrder`, `SaleOrderLine`, `Invoice`, `InvoiceLine`

Flow: `Quotation → Confirmed Order → Invoice → Paid`

---

### 🔲 CRM (`apps/crm`)
Inspired by Odoo's `crm` module.

Models: `Lead`, `Activity`, `Pipeline` (kanban stages)

---

### 🔲 Purchase (`apps/purchase`)
Inspired by Odoo's `purchase` module.

Models: `Vendor`, `PurchaseOrder`, `PurchaseOrderLine`, `Receipt`

Flow: `RFQ → Purchase Order → Received → Bill`

---

### 🔲 Accounting (`apps/accounting`)
Basic accounting — not a full GL, but enough to be impressive.

Models: `Account`, `Journal`, `JournalEntry`, `Payment`

---

### 🔲 Dashboard (`apps/dashboard`)
Analytics and KPIs pulled from all other modules.

Views: Revenue chart, top-selling products, low-stock alerts, order pipeline, recent activity feed.
Technology: HTMX for live partial updates, Chart.js for graphs.

---

## Architecture Decisions (recorded for future sessions)

| Decision | Choice | Why |
|---|---|---|
| Custom User model | UUID pk + email login | Better API security, avoids sequential ID leakage |
| Settings split | base / local / production | Clean separation, no accidental DEBUG=True in prod |
| App namespace | `apps.{name}` | All business apps live under `apps/`, avoids name collisions |
| Auth | JWT via djoser | Stateless, works for both HTMX and potential React/mobile later |
| Frontend | HTMX + Bootstrap 5 | Stays in Django ecosystem, faster to build, no JS build step |
| API docs | drf-spectacular | OpenAPI 3 standard, better than drf-yasg (which uses deprecated pkg_resources) |
| Stock tracking | Ledger pattern (StockMove) | Append-only, auditable — same approach as Odoo and most real ERPs |

---

## Known Issues / TODOs
- [ ] Docker + docker-compose not yet written
- [ ] Celery config (`config/celery.py`) not yet written
- [ ] Base HTML templates not yet created
- [ ] No tests written yet (pytest-django is installed and ready)
- [ ] GitHub Actions CI not yet configured

---

## For the Next Session

Pick up from **Inventory module**. The scaffold exists at `apps/inventory/` but models/views/serializers are all empty.

Start with:
1. `apps/inventory/models.py` — Category, Product, ProductAttribute, ProductVariant, Warehouse, StockMove
2. `apps/inventory/serializers.py`
3. `apps/inventory/views.py` (DRF ViewSets)
4. Register URLs in `config/api_urls.py`
5. Register in `apps/inventory/admin.py`
6. `python manage.py makemigrations inventory && python manage.py migrate`
