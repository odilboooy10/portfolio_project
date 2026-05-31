from django.urls import path

from .frontend_views import (
    UserChangeRoleView,
    UserDetailView,
    UserListView,
    UserToggleActiveView,
)

app_name = 'users'

urlpatterns = [
    path('',               UserListView.as_view(),       name='user-list'),
    path('<uuid:pk>/',      UserDetailView.as_view(),      name='user-detail'),
    path('<uuid:pk>/toggle-active/', UserToggleActiveView.as_view(), name='user-toggle-active'),
    path('<uuid:pk>/change-role/',   UserChangeRoleView.as_view(),   name='user-change-role'),
]
