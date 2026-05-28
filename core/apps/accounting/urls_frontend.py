from django.urls import path

from .frontend_views import (
    AccountListView,
    JournalCancelView,
    JournalDetailView,
    JournalListView,
    JournalPostView,
    PaymentListView,
)

app_name = 'accounting'

urlpatterns = [
    path('accounts/',                      AccountListView.as_view(),  name='account-list'),
    path('journals/',                      JournalListView.as_view(),  name='journal-list'),
    path('journals/<uuid:pk>/',            JournalDetailView.as_view(), name='journal-detail'),
    path('journals/<uuid:pk>/post/',       JournalPostView.as_view(),  name='journal-post'),
    path('journals/<uuid:pk>/cancel/',     JournalCancelView.as_view(), name='journal-cancel'),
    path('payments/',                      PaymentListView.as_view(),  name='payment-list'),
]
