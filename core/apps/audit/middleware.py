from .signals import set_current_user


class AuditUserMiddleware:
    """Injects the logged-in user into the audit signal context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            set_current_user(user)
        else:
            set_current_user(None)
        return self.get_response(request)
