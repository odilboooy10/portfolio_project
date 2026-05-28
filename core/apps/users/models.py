import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.audit.mixins import AuditableMixin


class User(AuditableMixin, AbstractUser):
    """
    Custom user model. Uses email as the login field.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Manager'
        SALES = 'sales', 'Sales'
        PURCHASE = 'purchase', 'Purchase'
        ACCOUNTANT = 'accountant', 'Accountant'
        VIEWER = 'viewer', 'Viewer'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER) or self.is_superuser
