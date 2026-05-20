from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, PurchaseOrderViewSet, ReceiptViewSet

router = DefaultRouter()
router.register('vendors', VendorViewSet, basename='vendor')
router.register('orders', PurchaseOrderViewSet, basename='purchase-order')
router.register('receipts', ReceiptViewSet, basename='receipt')

urlpatterns = router.urls
