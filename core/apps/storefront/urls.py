from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('signup/',   views.CustomerSignupView.as_view(), name='signup'),
    path('login/',    views.StoreLoginView.as_view(),     name='login'),
    path('logout/',   views.StoreLogoutView.as_view(),    name='logout'),
    path('pending/',  views.PendingApprovalView.as_view(), name='pending'),

    path('catalog/',                          views.CatalogView.as_view(),      name='catalog'),
    path('catalog/<uuid:pk>/',                views.ProductDetailView.as_view(), name='product-detail'),

    path('cart/',            views.CartView.as_view(),       name='cart'),
    path('cart/add/',        views.AddToCartView.as_view(),  name='add-to-cart'),
    path('cart/update/',     views.UpdateCartView.as_view(), name='update-cart'),

    path('checkout/',                         views.CheckoutView.as_view(),  name='checkout'),
    path('orders/',                           views.OrderListView.as_view(), name='order-list'),
    path('orders/<uuid:pk>/',                 views.OrderDetailView.as_view(), name='order-detail'),
]
