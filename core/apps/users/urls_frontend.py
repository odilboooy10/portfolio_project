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
    path('<int:pk>/',      UserDetailView.as_view(),      name='user-detail'),
    path('<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='user-toggle-active'),
    path('<int:pk>/change-role/',   UserChangeRoleView.as_view(),   name='user-change-role'),
]
