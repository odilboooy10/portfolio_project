from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from .models import User


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name')


@extend_schema_serializer(component_name='AppUser')
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'full_name', 'first_name', 'last_name', 'role', 'phone', 'avatar', 'is_verified')
        read_only_fields = ('id', 'is_verified')
