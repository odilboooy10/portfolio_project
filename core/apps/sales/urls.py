from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, QuotationViewSet, SaleOrderViewSet, InvoiceViewSet

router = DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')
router.register('quotations', QuotationViewSet, basename='quotation')
router.register('orders', SaleOrderViewSet, basename='sale-order')
router.register('invoices', InvoiceViewSet, basename='invoice')

urlpatterns = router.urls
