import pytest
from django.urls import reverse
from factories import UserFactory, ManagerUserFactory


@pytest.mark.django_db
class TestUserModel:
    def test_full_name_with_names(self):
        user = UserFactory(first_name='John', last_name='Doe')
        assert user.full_name == 'John Doe'

    def test_full_name_falls_back_to_email(self):
        user = UserFactory(first_name='', last_name='')
        assert user.full_name == user.email

    def test_is_admin_for_superuser(self):
        user = UserFactory(is_superuser=True, role='staff')
        assert user.is_admin is True

    def test_is_admin_for_admin_role(self):
        user = UserFactory(role='admin')
        assert user.is_admin is True

    def test_is_manager_includes_admin(self):
        user = UserFactory(role='admin')
        assert user.is_manager is True

    def test_is_manager_for_staff_role(self):
        user = UserFactory(role='staff')
        assert user.is_manager is True

    def test_staff_is_not_admin(self):
        user = UserFactory(role='staff')
        assert user.is_admin is False


@pytest.mark.django_db
class TestAuthAPI:
    def test_jwt_login_returns_tokens(self, api_client, manager_user):
        url = reverse('jwt-create')
        response = api_client.post(url, {'email': manager_user.email, 'password': 'pass123'})
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_with_wrong_password_fails(self, api_client, manager_user):
        url = reverse('jwt-create')
        response = api_client.post(url, {'email': manager_user.email, 'password': 'wrong'})
        assert response.status_code == 401

    def test_unauthenticated_request_denied(self, api_client):
        url = reverse('user-list')
        response = api_client.get(url)
        assert response.status_code == 401
