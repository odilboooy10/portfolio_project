from django.urls import path

from .frontend_views import (
    ProductDetailView,
    ProductListView,
    StockLevelListView,
    StockMoveCreateView,
)

app_name = 'inventory'

urlpatterns = [
    path('products/',              ProductListView.as_view(),    name='product-list'),
    path('products/<uuid:pk>/',    ProductDetailView.as_view(),  name='product-detail'),
    path('stock/',                 StockLevelListView.as_view(), name='stock-levels'),
    path('stock-move/',            StockMoveCreateView.as_view(), name='stock-move-create'),
]
