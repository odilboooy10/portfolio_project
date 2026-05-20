from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductAttributeViewSet, ProductAttributeValueViewSet,
    ProductViewSet, ProductVariantViewSet, WarehouseViewSet,
    StockMoveViewSet, StockLevelViewSet,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('attributes', ProductAttributeViewSet, basename='product-attribute')
router.register('attribute-values', ProductAttributeValueViewSet, basename='product-attribute-value')
router.register('products', ProductViewSet, basename='product')
router.register('variants', ProductVariantViewSet, basename='product-variant')
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('stock/moves', StockMoveViewSet, basename='stock-move')
router.register('stock/levels', StockLevelViewSet, basename='stock-level')

urlpatterns = router.urls
