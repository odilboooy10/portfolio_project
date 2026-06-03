"""
Central role-based permission classes for the ERP.

Permission Matrix:
                  Admin   Staff
─────────────────────────────────
All modules         ✅      ✅
Users management    ✅      ❌
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


def _can(user, *roles):
    return bool(
        user and user.is_authenticated
        and (getattr(user, 'role', None) in roles or user.is_superuser)
    )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin')


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin', 'staff')


class InventoryPermission(IsAuthenticated):
    pass


class SalesPermission(IsAuthenticated):
    pass


class CRMPermission(IsAuthenticated):
    pass


class PurchasePermission(IsAuthenticated):
    pass


class AccountingPermission(IsAuthenticated):
    pass


class UsersPermission(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin')
