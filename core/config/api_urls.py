from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.users.throttles import AuthRateThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRateThrottle]


urlpatterns = [
    # Auth (Djoser + JWT) — JWT token endpoints are rate-limited to 10/min per IP
    path('auth/', include('djoser.urls')),
    path('auth/jwt/create/', ThrottledTokenObtainPairView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', ThrottledTokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    path('auth/', include('djoser.urls.jwt')),

    # Inventory
    path('inventory/', include('apps.inventory.urls')),

    # Sales
    path('sales/', include('apps.sales.urls')),

    # CRM
    path('crm/', include('apps.crm.urls')),

    # Purchase
    path('purchase/', include('apps.purchase.urls')),

    # Accounting
    path('accounting/', include('apps.accounting.urls')),

    # Dashboard
    path('dashboard/', include('apps.dashboard.urls')),

    # API Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
