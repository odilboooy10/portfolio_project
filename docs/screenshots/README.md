# Screenshots — capture guide

Drop the finished images in this folder using the **exact filenames** below.
The root `README.md` already references these paths — once the files exist here,
the images render automatically (uncomment the block in the root README).

## Before capturing

Populate demo data so nothing looks empty:

```bash
cd core
python manage.py seed_demo --clear
```

Run both portals (see the root README) and log in with the seeded accounts:

- ERP admin — http://127.0.0.1:8000/ — `admin@erp.local` / `admin123`
- Storefront — http://127.0.0.1:8001/ — `customer@test.com` / `test1234`

Use a clean browser window at ~1440px wide, light mode, no dev-tools panel.
PNG, ideally ≤ 1600px wide so the README loads fast.

## Shot list

| Filename | Page | Port / URL |
|---|---|---|
| `dashboard.png` | ERP dashboard — KPI cards, revenue chart, pipeline chart | `:8000/dashboard/` |
| `inventory.png` | Product list (or product detail) | `:8000/inventory/products/` |
| `crm-kanban.png` | CRM pipeline kanban board | `:8000/crm/kanban/` |
| `sales-order.png` | A sale order detail with lines | `:8000/sales/orders/` → open one |
| `storefront-catalog.png` | CoreShop catalog with hero banner + product cards | `:8001/store/catalog/` |
| `storefront-product.png` | Product detail with reviews | `:8001/store/catalog/<id>/` |
| `storefront-checkout.png` | Checkout — progress bar + mock card | `:8001/store/checkout/` (add an item first) |

The first two (`dashboard.png`, `storefront-catalog.png`) are the highest-impact
pair for a recruiter skim — capture those first if you only do a couple.

## Optional: a hero/banner image

If you want a single wide banner at the very top of the README, name it
`banner.png` and uncomment the hero line in the root README.
