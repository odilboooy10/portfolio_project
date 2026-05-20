from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Auth (Djoser + JWT)
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),

    # Inventory
    path('inventory/', include('apps.inventory.urls')),

    # Sales
    path('sales/', include('apps.sales.urls')),

    # API Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
