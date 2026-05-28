from django.urls import path

from .frontend_views import (
    InvoiceCancelView,
    InvoiceDetailView,
    InvoiceListView,
    InvoiceMarkIssuedView,
    InvoiceMarkPaidView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
    OrderMarkDoneView,
    OrderMarkInProgressView,
)

app_name = 'sales'

urlpatterns = [
    path('orders/',                              OrderListView.as_view(),           name='order-list'),
    path('orders/<uuid:pk>/',                    OrderDetailView.as_view(),         name='order-detail'),
    path('orders/<uuid:pk>/in-progress/',        OrderMarkInProgressView.as_view(), name='order-in-progress'),
    path('orders/<uuid:pk>/done/',               OrderMarkDoneView.as_view(),       name='order-done'),
    path('orders/<uuid:pk>/cancel/',             OrderCancelView.as_view(),         name='order-cancel'),

    path('invoices/',                            InvoiceListView.as_view(),         name='invoice-list'),
    path('invoices/<uuid:pk>/',                  InvoiceDetailView.as_view(),       name='invoice-detail'),
    path('invoices/<uuid:pk>/issue/',            InvoiceMarkIssuedView.as_view(),   name='invoice-issue'),
    path('invoices/<uuid:pk>/paid/',             InvoiceMarkPaidView.as_view(),     name='invoice-paid'),
    path('invoices/<uuid:pk>/cancel/',           InvoiceCancelView.as_view(),       name='invoice-cancel'),
]
