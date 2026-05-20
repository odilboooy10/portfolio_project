from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, JournalViewSet, JournalEntryViewSet, PaymentViewSet

router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='account')
router.register('journals', JournalViewSet, basename='journal')
router.register('entries', JournalEntryViewSet, basename='journal-entry')
router.register('payments', PaymentViewSet, basename='payment')

urlpatterns = router.urls
