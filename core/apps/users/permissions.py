"""
Central role-based permission classes for the ERP.

Import from here in every app's views.py instead of defining local permission classes.

Permission Matrix:
                  Admin  Manager  Sales  Purchase  Accountant  Viewer
─────────────────────────────────────────────────────────────────────
Inventory  Read     ✅     ✅      ✅      ✅         ✅         ✅
Inventory  Write    ✅     ✅      ❌      ✅         ❌         ❌
Sales      Read     ✅     ✅      ✅      ❌         ✅         ✅
Sales      Write    ✅     ✅      ✅      ❌         ❌         ❌
CRM        Read     ✅     ✅      ✅      ❌         ❌         ✅
CRM        Write    ✅     ✅      ✅      ❌         ❌         ❌
Purchase   Read     ✅     ✅      ❌      ✅         ✅         ✅
Purchase   Write    ✅     ✅      ❌      ✅         ❌         ❌
Accounting Read     ✅     ✅      ❌      ❌         ✅         ❌
Accounting Write    ✅     ✅      ❌      ❌         ✅         ❌
Users      All      ✅     ❌      ❌      ❌         ❌         ❌
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


def _role(user):
    return getattr(user, 'role', None)


def _can(user, *roles):
    return bool(
        user and user.is_authenticated
        and (_role(user) in roles or user.is_superuser)
    )


# ── Generic ────────────────────────────────────────────────────────────────

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin')


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin', 'manager')


# ── Module-scoped ──────────────────────────────────────────────────────────

class InventoryPermission(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True  # all authenticated users can read
        return _can(request.user, 'admin', 'manager', 'purchase')


class SalesPermission(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return _can(request.user, 'admin', 'manager', 'sales', 'accountant', 'viewer')
        return _can(request.user, 'admin', 'manager', 'sales')


class CRMPermission(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return _can(request.user, 'admin', 'manager', 'sales', 'viewer')
        return _can(request.user, 'admin', 'manager', 'sales')


class PurchasePermission(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return _can(request.user, 'admin', 'manager', 'purchase', 'accountant', 'viewer')
        return _can(request.user, 'admin', 'manager', 'purchase')


class AccountingPermission(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return _can(request.user, 'admin', 'manager', 'accountant')


class UsersPermission(BasePermission):
    def has_permission(self, request, view):
        return _can(request.user, 'admin')
