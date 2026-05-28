from django.urls import path

from .frontend_views import (
    POCancelView,
    POConfirmView,
    PODetailView,
    POListView,
    POMarkBilledView,
    POReceiveView,
    VendorListView,
)

app_name = 'purchase'

urlpatterns = [
    path('vendors/',                      VendorListView.as_view(),  name='vendor-list'),
    path('orders/',                       POListView.as_view(),      name='po-list'),
    path('orders/<uuid:pk>/',             PODetailView.as_view(),    name='po-detail'),
    path('orders/<uuid:pk>/confirm/',     POConfirmView.as_view(),   name='po-confirm'),
    path('orders/<uuid:pk>/receive/',     POReceiveView.as_view(),   name='po-receive'),
    path('orders/<uuid:pk>/billed/',      POMarkBilledView.as_view(), name='po-billed'),
    path('orders/<uuid:pk>/cancel/',      POCancelView.as_view(),    name='po-cancel'),
]
