# ERP Core

A full-featured, Odoo-inspired ERP suite built with Django and Django REST Framework — plus a customer-facing storefront that runs off the same backend. Built as a portfolio project to demonstrate production-grade backend and fullstack engineering.

<!--
Add screenshots here once captured, e.g.:
![Dashboard](docs/screenshots/dashboard.png)
![Storefront](docs/screenshots/storefront.png)
-->

---

## What it is

Two applications, one Django backend:

- **ERP admin panel** (port `8000`) — internal business management: sales, inventory, CRM, purchasing, accounting, and an analytics dashboard. Admin-only.
- **CoreShop storefront** (port `8001`) — a customer-facing shop with catalog, cart, checkout, order tracking, product likes and reviews. Customers only.

The two are isolated by a routing middleware and per-port session cookies, so an admin session on `8000` and a customer session on `8001` never collide.

---

## Highlights

- **36 models** across 10 Django apps, **66 tests**, **0 failures**
- **REST API** with JWT auth and a live OpenAPI 3 schema (Swagger + Redoc)
- **Dual-portal architecture** — internal ERP and public storefront from one codebase, cleanly separated
- **Dockerized** — Postgres + Redis + Gunicorn + Celery + Nginx via `docker-compose`
- **CI** on GitHub Actions
- **Design system** — token-based CSS for the ERP; a separate premium design language ("CoreShop") for the storefront

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework 3.14 |
| Auth | JWT (simplejwt) + Djoser; email-based login |
| API docs | drf-spectacular (OpenAPI 3 → Swagger UI + Redoc) |
| Database | PostgreSQL 15 |
| Async | Celery + Redis, django-celery-beat / -results |
| Frontend | Django templates + Bootstrap 5 + HTMX + Chart.js |
| PDF | WeasyPrint (invoices) |
| Deploy | Docker, Gunicorn, Nginx, GitHub Actions CI |

---

## Modules

| Module | What it does |
|---|---|
| **Users** | Custom user model — UUID PKs, email login, role-based access (`admin` / `staff` / `customer`), customer approval flow |
| **Inventory** | Products, variants, categories, warehouses, stock levels; append-only `StockMove` ledger; admin-only product CRUD |
| **Sales** | Sale orders → invoices, order lines, status pipeline, PDF invoices |
| **CRM** | Leads, pipeline kanban with drag stages, activities, priority + probability tracking |
| **Purchase** | Vendors, purchase orders, RFQ → receipt flow |
| **Accounting** | Chart of accounts, journals, payments |
| **Dashboard** | Revenue chart, KPI cards, order-pipeline chart, low-stock alerts, recent-activity feed |
| **Storefront** | Customer catalog, cart, checkout, order tracking, likes + reviews (reviews gated to delivered orders) |
| **Audit** | Automatic audit logging via middleware |
| **Webhooks** | Outbound webhook delivery |

---

## Architecture notes

| Decision | Choice | Why |
|---|---|---|
| Primary keys | UUID on every model | Avoids sequential-ID leakage; safer public URLs |
| User model | Email login + role field | Set up before first migration; `USERNAME_FIELD = 'email'` |
| Serializers | Split `List` / `Detail` per module | Lean list responses, avoids N+1 |
| Settings | `base` / `local` / `production` split | No accidental `DEBUG=True` in prod |
| Stock | Append-only `StockMove` ledger | Auditable; levels are derived, not mutated in place |
| Portal routing | `PortRoutingMiddleware` + per-port `SESSION_COOKIE_NAME` | ERP and storefront share a backend but never share a session |
| Reviews | Gated to `done` (delivered) orders | Customers can only review what they actually received |

---

## Quick start

### Option A — Docker (everything)

```bash
cp .env.example .env          # then edit SECRET_KEY etc.
docker compose up --build
```

Brings up Postgres, Redis, Gunicorn (web), Celery, and Nginx. The app is served on port `80`.

### Option B — Local development

**Prerequisites:** Python 3.11, PostgreSQL 15, Redis.

```bash
# 1. Environment
cp .env.example .env          # .env must sit in the repo root, one level above core/
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements/local.txt

# 2. Database
cd core
python manage.py migrate
python manage.py createsuperuser

# 3. Run BOTH portals (separate terminals) — note the separate settings
#    modules; each isolates its own session cookie.

# ERP admin panel — admin only
DJANGO_SETTINGS_MODULE=config.settings.local_erp python manage.py runserver 8000

# CoreShop storefront — customers only
DJANGO_SETTINGS_MODULE=config.settings.local_store python manage.py runserver 8001

# 4. Celery worker (optional, separate terminal)
celery -A config worker -l info
```

> The two portals **must** use `local_erp` and `local_store` settings rather than plain `local`. They set different `SESSION_COOKIE_NAME` values so logging in on one port doesn't overwrite the session on the other.

---

## URLs

| URL | What |
|---|---|
| `http://127.0.0.1:8000/` | ERP admin panel (redirects to login) |
| `http://127.0.0.1:8001/` | CoreShop storefront |
| `/api/v1/docs/` | Swagger UI |
| `/api/v1/redoc/` | Redoc |
| `/admin/` | Django admin |

---

## Testing

```bash
cd core
python manage.py test
```

66 tests, currently all passing.

---

## Project structure

```
portfolio-project/
├── docker-compose.yml       # Postgres + Redis + web + celery + nginx
├── Dockerfile
├── nginx/                   # reverse-proxy config
├── requirements/            # base / local / production
├── docs/                    # architecture, design system, feature logic
└── core/                    # Django project root (manage.py)
    ├── config/
    │   ├── settings/        # base, local, local_erp, local_store, production
    │   ├── middleware.py    # PortRoutingMiddleware
    │   └── urls.py
    ├── apps/                # users, inventory, sales, crm, purchase,
    │                        # accounting, dashboard, storefront, audit, webhooks
    ├── templates/           # ERP + storefront templates
    └── static/css/theme.css # ERP design tokens
```

---

## Further docs

Deeper design and domain notes live in [`docs/`](docs/) — architecture, design system, feature logic, and storefront documentation.

---

*Built as a portfolio project. Domain modeled on Odoo Community Edition; all code is original.*
