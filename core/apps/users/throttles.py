"""
Custom throttle classes for scoped rate limiting.

Usage in a view:
    throttle_classes = [AuthRateThrottle]
    throttle_classes = [WriteRateThrottle]
"""
from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """10 requests/min per IP — applied on JWT obtain/refresh endpoints."""
    scope = 'auth'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class WriteRateThrottle(SimpleRateThrottle):
    """60 write requests/min per user — applied on POST/PATCH/DELETE."""
    scope = 'write'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def allow_request(self, request, view):
        # Only throttle mutating methods
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return super().allow_request(request, view)
