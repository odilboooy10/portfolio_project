from django.urls import path
from .views import (
    DashboardSummaryView,
    RevenueChartView,
    TopProductsView,
    LowStockView,
    RecentActivityView,
    OrderPipelineView,
)

urlpatterns = [
    path('summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('revenue/', RevenueChartView.as_view(), name='dashboard-revenue'),
    path('top-products/', TopProductsView.as_view(), name='dashboard-top-products'),
    path('low-stock/', LowStockView.as_view(), name='dashboard-low-stock'),
    path('activity/', RecentActivityView.as_view(), name='dashboard-activity'),
    path('pipeline/', OrderPipelineView.as_view(), name='dashboard-pipeline'),
]
