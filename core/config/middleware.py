from django.shortcuts import redirect


class PortRoutingMiddleware:
    """
    Port 8001 (storefront): redirect non-store paths to /store/login/.
    Port 8000 (ERP):        redirect /store/ paths to /login/;
                            redirect authenticated non-admins to /login/
                            so a customer session from port 8001 can't bleed in.
    CustomerRequiredMixin handles role enforcement inside the storefront.
    """
    STORE_PREFIXES = ('/store/', '/api/', '/admin/', '/__debug__/')
    ERP_EXEMPT     = ('/login/', '/logout/', '/api/', '/admin/', '/__debug__/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        port = request.META.get('SERVER_PORT')
        path = request.path_info

        if port == '8001':
            if not any(path.startswith(p) for p in self.STORE_PREFIXES):
                return redirect('/store/login/')

        elif port == '8000':
            if path.startswith('/store/'):
                return redirect('/login/')
            if (request.user.is_authenticated
                    and not any(path.startswith(p) for p in self.ERP_EXEMPT)
                    and getattr(request.user, 'role', None) != 'admin'):
                return redirect('/login/')

        return self.get_response(request)
