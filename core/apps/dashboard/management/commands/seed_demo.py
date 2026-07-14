"""
Populate the database with realistic demo data so a fresh install / deploy
isn't empty. Idempotent for master data (categories, warehouses, accounts,
etc. via get_or_create); transactional docs (orders, invoices, POs) are only
created when none exist, unless --clear is passed to reset first.

    python manage.py seed_demo
    python manage.py seed_demo --clear      # wipe demo data, then reseed
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.users.models import User
from apps.inventory.models import (
    Category, ProductAttribute, ProductAttributeValue, Product,
    ProductVariant, Warehouse, StockMove, StockLevel,
)
from apps.sales.models import Customer, SaleOrder, SaleOrderLine, Invoice, InvoiceLine
from apps.crm.models import Pipeline, Lead, Activity
from apps.purchase.models import (
    Vendor, PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine,
)
from apps.accounting.models import Account, Journal, JournalEntry, JournalEntryLine, Payment
from apps.storefront.models import ProductLike, ProductReview

RNG = random.Random(42)          # deterministic output
D = lambda v: Decimal(str(v))    # noqa: E731


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing demo data before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.now = timezone.now()

        if options['clear']:
            self._clear()

        staff = self._users()
        warehouse, variants = self._inventory()
        customers = self._customers()
        self._sales(customers, variants, staff)
        self._crm(customers, staff)
        self._purchasing(variants, staff)
        self._accounting()
        self._storefront(variants)

        self.stdout.write(self.style.SUCCESS('\nDemo data seeded successfully.'))
        self._print_credentials()

    # ── Clearing ─────────────────────────────────────────────────────────
    def _clear(self):
        self.stdout.write('Clearing existing demo data…')
        for model in (
            ProductReview, ProductLike,
            Payment, JournalEntryLine, JournalEntry, Journal, Account,
            ReceiptLine, Receipt, PurchaseOrderLine, PurchaseOrder, Vendor,
            Activity, Lead, Pipeline,
            InvoiceLine, Invoice, SaleOrderLine, SaleOrder, Customer,
            StockMove, StockLevel, ProductVariant, Product,
            ProductAttributeValue, ProductAttribute, Category, Warehouse,
        ):
            model.objects.all().delete()
        # keep superusers; drop demo staff/customers
        User.objects.filter(is_superuser=False).delete()

    # ── Users ────────────────────────────────────────────────────────────
    def _users(self):
        admin, created = User.objects.get_or_create(
            email='admin@erp.local',
            defaults={'username': 'admin', 'role': User.Role.ADMIN,
                      'first_name': 'Ada', 'last_name': 'Admin',
                      'is_staff': True, 'is_superuser': True, 'is_verified': True},
        )
        if created:
            admin.set_password('admin123')
            admin.save()

        staff = []
        for uname, email, first, last in [
            ('manager', 'manager@erp.local', 'Maya', 'Manager'),
            ('sales',   'sales@erp.local',   'Sam',  'Sales'),
        ]:
            u, created = User.objects.get_or_create(
                email=email,
                defaults={'username': uname, 'role': User.Role.STAFF,
                          'first_name': first, 'last_name': last,
                          'is_staff': True, 'is_verified': True},
            )
            if created:
                u.set_password('admin123')
                u.save()
            staff.append(u)
        self.stdout.write(f'  users: 1 admin, {len(staff)} staff')
        return staff

    # ── Inventory ────────────────────────────────────────────────────────
    def _inventory(self):
        warehouse, _ = Warehouse.objects.get_or_create(
            code='WH-MAIN', defaults={'name': 'Main Warehouse',
                                      'address': '100 Commerce Ave, Metro City'},
        )

        cats = {}
        for name in ['Apparel', 'Electronics', 'Home & Living', 'Accessories']:
            cats[name], _ = Category.objects.get_or_create(name=name)

        size, _ = ProductAttribute.objects.get_or_create(name='Size')
        color, _ = ProductAttribute.objects.get_or_create(name='Color')
        sizes = [ProductAttributeValue.objects.get_or_create(attribute=size, value=v)[0]
                 for v in ['S', 'M', 'L', 'XL']]
        colors = [ProductAttributeValue.objects.get_or_create(attribute=color, value=v)[0]
                  for v in ['Black', 'White', 'Blue', 'Sand']]

        catalog = [
            ('Classic Cotton Tee',      'Apparel',       19.90),
            ('Merino Wool Sweater',     'Apparel',       89.00),
            ('Everyday Chino Pants',    'Apparel',       54.50),
            ('Wireless Headphones',     'Electronics',  129.00),
            ('Mechanical Keyboard',     'Electronics',   99.00),
            ('USB-C Charging Hub',      'Electronics',   45.00),
            ('Ceramic Pour-Over Set',   'Home & Living', 38.00),
            ('Linen Throw Blanket',     'Home & Living', 62.00),
            ('Scented Soy Candle',      'Home & Living', 24.00),
            ('Leather Card Wallet',     'Accessories',   34.00),
            ('Canvas Weekender Bag',    'Accessories',   79.00),
            ('Stainless Water Bottle',  'Accessories',   28.00),
        ]

        all_variants = []
        if Product.objects.exists():
            all_variants = list(ProductVariant.objects.all())
            self.stdout.write(f'  inventory: exists ({len(all_variants)} variants) — skipped')
            return warehouse, all_variants

        low_targets = set(RNG.sample(range(len(catalog)), 3))  # 3 products low/zero stock
        for idx, (name, cat, price) in enumerate(catalog):
            slug = name.lower().replace(' ', '-').replace('/', '')
            product = Product.objects.create(
                name=name, sku=f'SKU-{idx + 1:03d}', category=cats[cat],
                base_price=D(price), is_active=True,
                description=f'{name} — a demo catalog product for the CoreShop storefront.',
            )
            n_variants = RNG.choice([1, 2, 3])
            for v in range(n_variants):
                variant = ProductVariant.objects.create(
                    product=product, sku=f'{product.sku}-V{v + 1}',
                    price_override=None if v == 0 else D(round(price + RNG.uniform(-3, 8), 2)),
                    is_active=True,
                )
                variant.attribute_values.add(RNG.choice(sizes), RNG.choice(colors))

                if idx in low_targets:
                    qty = D(RNG.choice([0, 2, 3, 5]))
                else:
                    qty = D(RNG.randint(20, 200))
                StockLevel.objects.create(variant=variant, warehouse=warehouse, quantity=qty)
                if qty > 0:
                    StockMove.objects.create(
                        variant=variant, warehouse=warehouse,
                        move_type=StockMove.MoveType.IN, quantity=qty,
                        reference='Initial stock', note='Seeded opening balance',
                    )
                all_variants.append(variant)
        self.stdout.write(f'  inventory: {len(catalog)} products, {len(all_variants)} variants')
        return warehouse, all_variants

    # ── Customers ────────────────────────────────────────────────────────
    def _customers(self):
        data = [
            ('Northwind Traders',  'orders@northwind.example',  'Grace Hopper',  'Northwind Traders'),
            ('Acme Corporation',   'buy@acme.example',          'Wile Coyote',   'Acme Corporation'),
            ('Globex Industries',  'ap@globex.example',         'Hank Scorpio',  'Globex Industries'),
            ('Umbra Retail',       'hello@umbra.example',       'Nadia Ito',     'Umbra Retail'),
            ('Cedar & Co.',        'accounts@cedar.example',    'Leo Marx',      'Cedar & Co.'),
            ('Bright Studio',      'team@brightstudio.example', 'Priya Nair',    'Bright Studio'),
            ('Harbor Foods',       'supply@harbor.example',     'Tom Reyes',     'Harbor Foods'),
            ('Vertex Labs',        'proc@vertex.example',       'Ivy Chen',      'Vertex Labs'),
        ]
        customers = []
        for name, email, contact, company in data:
            c, _ = Customer.objects.get_or_create(
                email=email,
                defaults={'name': name, 'company': company,
                          'phone': f'+1-555-{RNG.randint(1000, 9999)}',
                          'address': f'{RNG.randint(10, 999)} Market St, Suite {RNG.randint(1, 40)}'},
            )
            customers.append(c)
        self.stdout.write(f'  customers: {len(customers)}')
        return customers

    # ── Sales ────────────────────────────────────────────────────────────
    # References are generated from the latest confirmed_at/created_at, so we
    # create every document with default (now) timestamps first, then backdate
    # in a second pass — otherwise backdating mid-loop breaks reference numbering.
    def _sales(self, customers, variants, staff):
        if SaleOrder.objects.exists():
            self.stdout.write('  sales: exists — skipped')
            return

        statuses = (
            [SaleOrder.Status.DONE] * 8 +
            [SaleOrder.Status.IN_PROGRESS] * 4 +
            [SaleOrder.Status.CONFIRMED] * 4 +
            [SaleOrder.Status.CANCELLED] * 2
        )
        RNG.shuffle(statuses)

        order_backdates = {}   # order.pk -> confirmed_at
        invoice_backdates = {}  # invoice.pk -> created_at
        n_paid = n_issued = n_overdue = 0
        done_seen = 0

        for status in statuses:
            # Force the first few delivered orders to be recent so the dashboard's
            # "Revenue this month" card and the latest chart bar aren't empty.
            if status == SaleOrder.Status.DONE and done_seen < 3:
                confirmed_at = self.now - timedelta(days=RNG.randint(1, 16))
                done_seen += 1
            else:
                confirmed_at = self.now - timedelta(days=RNG.randint(3, 330))
            order = SaleOrder.objects.create(
                customer=RNG.choice(customers), status=status,
                discount=D(RNG.choice([0, 0, 0, 5, 10])),
                confirmed_by=RNG.choice(staff),
            )
            order_backdates[order.pk] = confirmed_at

            for variant in RNG.sample(variants, RNG.randint(1, 4)):
                SaleOrderLine.objects.create(
                    order=order, variant=variant,
                    quantity=D(RNG.randint(1, 6)),
                    unit_price=variant.effective_price,
                )

            if status in (SaleOrder.Status.DONE, SaleOrder.Status.CONFIRMED):
                inv = self._invoice_for(order, confirmed_at, status)
                invoice_backdates[inv.pk] = confirmed_at + timedelta(days=1)
                if inv.status == Invoice.Status.PAID:
                    n_paid += 1
                else:
                    n_issued += 1
                    if inv.due_date and inv.due_date < self.now.date():
                        n_overdue += 1

        # Second pass: backdate timestamps now that all references are assigned.
        for pk, dt in order_backdates.items():
            SaleOrder.objects.filter(pk=pk).update(confirmed_at=dt)
        for pk, dt in invoice_backdates.items():
            Invoice.objects.filter(pk=pk).update(created_at=dt)

        self.stdout.write(
            f'  sales: {len(statuses)} orders, invoices ({n_paid} paid, '
            f'{n_issued} issued incl. {n_overdue} overdue)'
        )

    def _invoice_for(self, order, confirmed_at, order_status):
        invoice = Invoice.objects.create(
            sale_order=order, customer=order.customer,
            status=Invoice.Status.DRAFT, discount=order.discount,
            issue_date=(confirmed_at + timedelta(days=1)).date(),
            due_date=(confirmed_at + timedelta(days=15)).date(),
        )
        for line in order.lines.all():
            InvoiceLine.objects.create(
                invoice=invoice, variant=line.variant,
                quantity=line.quantity, unit_price=line.unit_price,
            )

        if order_status == SaleOrder.Status.DONE:
            # Delivered orders → paid; spread paid_at across the year for the chart,
            # clamped so a recent order never gets a future payment date.
            paid_at = confirmed_at + timedelta(days=RNG.randint(2, 12))
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = min(paid_at, self.now - timedelta(hours=1))
            invoice.save(update_fields=['status', 'paid_at'])
        else:
            # Confirmed (not delivered) → issued, ~40% overdue
            invoice.status = Invoice.Status.ISSUED
            if RNG.random() < 0.4:
                invoice.due_date = self.now.date() - timedelta(days=RNG.randint(2, 20))
            invoice.save(update_fields=['status', 'due_date'])
        return invoice

    # ── CRM ──────────────────────────────────────────────────────────────
    def _crm(self, customers, staff):
        stages_def = [
            ('New',         1, 10, False, False),
            ('Qualified',   2, 30, False, False),
            ('Proposition', 3, 60, False, False),
            ('Won',         4, 100, True, False),
            ('Lost',        5, 0, False, True),
        ]
        stages = {}
        for name, order, prob, won, lost in stages_def:
            stages[name], _ = Pipeline.objects.get_or_create(
                name=name,
                defaults={'order': order, 'probability': D(prob),
                          'is_won': won, 'is_lost': lost},
            )

        if Lead.objects.exists():
            self.stdout.write('  crm: leads exist — skipped')
            return

        titles = [
            'Bulk apparel order', 'Office electronics refresh', 'Annual supply contract',
            'New store fit-out', 'Wholesale accessories deal', 'Seasonal gift bundles',
            'Cafe equipment package', 'Corporate merch program', 'Trade show sample kit',
            'Replacement parts contract', 'Loyalty rewards catalog', 'Warehouse restock',
        ]
        priorities = [Lead.Priority.LOW, Lead.Priority.MEDIUM, Lead.Priority.HIGH]
        active_stages = ['New', 'Qualified', 'Proposition']
        n = 0
        for title in titles:
            roll = RNG.random()
            if roll < 0.6:
                stage_name = RNG.choice(active_stages)
            elif roll < 0.8:
                stage_name = 'Won'
            else:
                stage_name = 'Lost'
            stage = stages[stage_name]
            customer = RNG.choice(customers)
            lead = Lead.objects.create(
                name=title,
                contact_name=customer.name.split()[0] + ' Buyer',
                contact_email=customer.email,
                company=customer.company,
                pipeline=stage,
                priority=RNG.choice(priorities),
                expected_revenue=D(RNG.choice([1500, 3000, 5000, 8500, 12000, 20000])),
                probability=stage.probability,
                assigned_to=RNG.choice(staff),
                customer=customer,
                expected_close_date=(self.now + timedelta(days=RNG.randint(-10, 60))).date(),
            )
            if stage_name == 'Won':
                Lead.objects.filter(pk=lead.pk).update(
                    won_at=self.now - timedelta(days=RNG.randint(1, 40)))
            elif stage_name == 'Lost':
                Lead.objects.filter(pk=lead.pk).update(
                    lost_at=self.now - timedelta(days=RNG.randint(1, 40)),
                    lost_reason='Went with a competitor.')

            # A pending activity on some active leads → feeds the activity view
            if stage_name in active_stages and RNG.random() < 0.6:
                Activity.objects.create(
                    lead=lead,
                    activity_type=RNG.choice([Activity.ActivityType.CALL,
                                              Activity.ActivityType.EMAIL,
                                              Activity.ActivityType.MEETING]),
                    title=f'Follow up on {title.lower()}',
                    due_date=self.now + timedelta(days=RNG.randint(1, 14)),
                    assigned_to=lead.assigned_to,
                )
            n += 1
        self.stdout.write(f'  crm: 5 stages, {n} leads')

    # ── Purchasing ───────────────────────────────────────────────────────
    def _purchasing(self, variants, staff):
        vendors_def = [
            ('Pacific Textiles',   'sales@pacifictex.example'),
            ('Circuit Supply Co.', 'orders@circuitsupply.example'),
            ('Homeware Imports',   'wholesale@homeware.example'),
            ('LeatherWorks Ltd.',  'contact@leatherworks.example'),
            ('BottleWorks',        'hello@bottleworks.example'),
        ]
        vendors = []
        for name, email in vendors_def:
            v, _ = Vendor.objects.get_or_create(
                email=email,
                defaults={'name': name, 'company': name,
                          'payment_terms': RNG.choice(['Net 15', 'Net 30', 'Net 45'])},
            )
            vendors.append(v)

        if PurchaseOrder.objects.exists():
            self.stdout.write('  purchasing: exists — skipped')
            return

        statuses = ([PurchaseOrder.Status.RECEIVED] * 3 +
                    [PurchaseOrder.Status.CONFIRMED] * 3 +
                    [PurchaseOrder.Status.RFQ] * 2)
        RNG.shuffle(statuses)
        po_backdates = {}
        for status in statuses:
            po = PurchaseOrder.objects.create(
                vendor=RNG.choice(vendors), status=status,
                expected_delivery=(self.now + timedelta(days=RNG.randint(5, 30))).date(),
                created_by=RNG.choice(staff),
            )
            po_backdates[po.pk] = self.now - timedelta(days=RNG.randint(5, 120))
            for variant in RNG.sample(variants, RNG.randint(1, 3)):
                qty = D(RNG.randint(10, 100))
                PurchaseOrderLine.objects.create(
                    order=po, variant=variant, quantity=qty,
                    unit_price=D(round(float(variant.effective_price) * 0.55, 2)),
                    received_qty=qty if status == PurchaseOrder.Status.RECEIVED else D(0),
                )
        for pk, dt in po_backdates.items():  # backdate after references assigned
            PurchaseOrder.objects.filter(pk=pk).update(created_at=dt)
        self.stdout.write(f'  purchasing: {len(vendors)} vendors, {len(statuses)} POs')

    # ── Accounting ───────────────────────────────────────────────────────
    def _accounting(self):
        accounts_def = [
            ('1000', 'Cash', Account.AccountType.ASSET),
            ('1100', 'Accounts Receivable', Account.AccountType.ASSET),
            ('1200', 'Inventory', Account.AccountType.ASSET),
            ('2000', 'Accounts Payable', Account.AccountType.LIABILITY),
            ('3000', 'Owner Equity', Account.AccountType.EQUITY),
            ('4000', 'Sales Revenue', Account.AccountType.REVENUE),
            ('5000', 'Cost of Goods Sold', Account.AccountType.EXPENSE),
            ('6000', 'Operating Expenses', Account.AccountType.EXPENSE),
        ]
        accounts = {}
        for code, name, atype in accounts_def:
            accounts[code], _ = Account.objects.get_or_create(
                code=code, defaults={'name': name, 'account_type': atype})

        journals = {}
        for name, code, jtype in [
            ('Sales Journal', 'SAL', Journal.JournalType.SALES),
            ('Purchase Journal', 'PUR', Journal.JournalType.PURCHASE),
            ('Bank Journal', 'BNK', Journal.JournalType.BANK),
        ]:
            journals[code], _ = Journal.objects.get_or_create(
                code=code, defaults={'name': name, 'journal_type': jtype})

        if not JournalEntry.objects.exists():
            # A few balanced entries from paid invoices
            paid = Invoice.objects.filter(status=Invoice.Status.PAID)[:5]
            for inv in paid:
                amount = inv.total
                entry = JournalEntry.objects.create(
                    journal=journals['SAL'], status=JournalEntry.Status.POSTED,
                    date=(inv.paid_at or self.now).date(), invoice=inv,
                    note=f'Revenue recognition for {inv.reference}',
                )
                JournalEntryLine.objects.create(
                    entry=entry, account=accounts['1100'],
                    description='Accounts receivable', debit=amount, credit=D(0))
                JournalEntryLine.objects.create(
                    entry=entry, account=accounts['4000'],
                    description='Sales revenue', debit=D(0), credit=amount)

        if not Payment.objects.exists():
            for inv in Invoice.objects.filter(status=Invoice.Status.PAID)[:6]:
                Payment.objects.create(
                    payment_type=Payment.PaymentType.INBOUND,
                    payment_method=RNG.choice([Payment.PaymentMethod.BANK,
                                               Payment.PaymentMethod.CARD]),
                    amount=inv.total, date=(inv.paid_at or self.now).date(),
                    journal=journals['BNK'], invoice=inv,
                )
        self.stdout.write(f'  accounting: {len(accounts)} accounts, 3 journals, entries + payments')

    # ── Storefront ───────────────────────────────────────────────────────
    def _storefront(self, variants):
        shoppers_def = [
            ('shopper1', 'customer@test.com',   'Chris', 'Buyer',  True),
            ('shopper2', 'jordan@test.com',     'Jordan', 'Lee',   True),
            ('shopper3', 'sam.k@test.com',      'Sam',   'Kaur',   True),
            ('shopper4', 'pending@test.com',    'Pat',   'Waiting', False),  # awaiting approval
        ]
        shoppers = []
        for uname, email, first, last, active in shoppers_def:
            u, created = User.objects.get_or_create(
                email=email,
                defaults={'username': uname, 'role': User.Role.CUSTOMER,
                          'first_name': first, 'last_name': last,
                          'is_active': active, 'is_verified': active},
            )
            if created:
                u.set_password('test1234')
                u.save()
            if active:
                shoppers.append(u)

        products = list({v.product for v in variants})
        if products and not ProductReview.objects.exists():
            review_bodies = [
                'Exactly as described, great quality.',
                'Fast shipping and works perfectly.',
                'Good value for the price. Would buy again.',
                'Solid build, happy with the purchase.',
                'Nice product but packaging could be better.',
            ]
            for shopper in shoppers:
                for product in RNG.sample(products, min(4, len(products))):
                    ProductLike.objects.get_or_create(user=shopper, product=product)
                for product in RNG.sample(products, min(3, len(products))):
                    ProductReview.objects.get_or_create(
                        user=shopper, product=product,
                        defaults={'rating': RNG.randint(3, 5),
                                  'body': RNG.choice(review_bodies)},
                    )
        self.stdout.write(f'  storefront: {len(shoppers)} approved shoppers (+1 pending), likes + reviews')

    # ── Output ───────────────────────────────────────────────────────────
    def _print_credentials(self):
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Login credentials:'))
        self.stdout.write('  ERP admin  (:8000)  admin@erp.local     / admin123')
        self.stdout.write('  ERP staff  (:8000)  manager@erp.local   / admin123   (blocked — admin only)')
        self.stdout.write('  Storefront (:8001)  customer@test.com   / test1234')
        self.stdout.write('  Storefront (:8001)  pending@test.com    / test1234   (awaiting approval)')
