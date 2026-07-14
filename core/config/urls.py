from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from views import LoginView, LogoutView, RootView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Frontend auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Frontend pages
    path('', RootView.as_view()),
    path('dashboard/', include('apps.dashboard.urls_frontend', namespace='dashboard')),
    path('sales/',     include('apps.sales.urls_frontend',     namespace='sales')),
    path('crm/',       include('apps.crm.urls_frontend',       namespace='crm')),
    path('inventory/', include('apps.inventory.urls_frontend', namespace='inventory')),
    path('purchase/',    include('apps.purchase.urls_frontend',    namespace='purchase')),
    path('accounting/',  include('apps.accounting.urls_frontend',  namespace='accounting')),
    path('users/',       include('apps.users.urls_frontend',       namespace='users')),
    path('store/',       include('apps.storefront.urls',            namespace='store')),

    # API v1
    path('api/v1/', include('config.api_urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
