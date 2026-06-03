from django.urls import path

from .frontend_views import (
    ProductCreateView,
    ProductDeleteView,
    ProductDetailView,
    ProductListView,
    ProductUpdateView,
    StockLevelListView,
    StockMoveCreateView,
)

app_name = 'inventory'

urlpatterns = [
    path('products/',                    ProductListView.as_view(),    name='product-list'),
    path('products/new/',                ProductCreateView.as_view(),  name='product-create'),
    path('products/<uuid:pk>/',          ProductDetailView.as_view(),  name='product-detail'),
    path('products/<uuid:pk>/edit/',     ProductUpdateView.as_view(),  name='product-edit'),
    path('products/<uuid:pk>/delete/',   ProductDeleteView.as_view(),  name='product-delete'),
    path('stock/',                       StockLevelListView.as_view(), name='stock-levels'),
    path('stock-move/',                  StockMoveCreateView.as_view(), name='stock-move-create'),
]
