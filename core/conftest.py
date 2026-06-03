import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    from apps.users.models import User
    return User.objects.create_superuser(
        email='admin@erp.local',
        username='admin',
        password='admin123',
        role='admin',
    )


@pytest.fixture
def manager_user(db):
    from apps.users.models import User
    return User.objects.create_user(
        email='manager@erp.local',
        username='manager',
        password='pass123',
        role='staff',
    )


@pytest.fixture
def sales_user(db):
    from apps.users.models import User
    return User.objects.create_user(
        email='sales@erp.local',
        username='salesrep',
        password='pass123',
        role='staff',
    )


@pytest.fixture
def auth_client(api_client, manager_user):
    """Authenticated API client as a manager (can write)."""
    api_client.force_authenticate(user=manager_user)
    return api_client


@pytest.fixture
def readonly_client(api_client, sales_user):
    """Authenticated API client as a sales user (read-only)."""
    api_client.force_authenticate(user=sales_user)
    return api_client
