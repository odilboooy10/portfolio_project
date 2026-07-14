from django.conf import settings
from django.shortcuts import redirect


def portal_for(request):
    """
    Return the portal a request targets: 'erp', 'store', or None (unknown).

    Production routes by hostname when settings.ERP_HOST / STORE_HOST are set
    (different subdomains → separate host-only session cookies, no bleed).
    Local dev falls back to port 8000 (ERP) / 8001 (store).
    """
    erp_host = getattr(settings, 'ERP_HOST', '')
    store_host = getattr(settings, 'STORE_HOST', '')

    if erp_host or store_host:
        host = request.get_host().split(':')[0]
        if host == store_host:
            return 'store'
        if host == erp_host:
            return 'erp'
        return None

    port = request.META.get('SERVER_PORT')
    if port == '8001':
        return 'store'
    if port == '8000':
        return 'erp'
    return None


class PortRoutingMiddleware:
    """
    Routes a shared backend into two portals:

      • ERP   — admin only  (/login/, dashboard, modules)
      • Store — customers    (/store/...)

    Portal detection:
      • Production — by hostname, when settings.ERP_HOST / STORE_HOST are set
        (e.g. admin.example.com vs shop.example.com). Different subdomains get
        separate host-only session cookies for free, so no session bleed.
      • Local dev — by port, 8000 (ERP) vs 8001 (store), when hosts are unset.

    Behaviour per portal:
      • Store: redirect non-store paths to /store/login/.
      • ERP:   redirect /store/ paths to /login/; redirect authenticated
               non-admins off ERP paths to /login/.

    Never calls logout() — CustomerRequiredMixin enforces roles inside the store.
    """
    STORE_PREFIXES = ('/store/', '/api/', '/admin/', '/__debug__/')
    ERP_EXEMPT     = ('/login/', '/logout/', '/api/', '/admin/', '/__debug__/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        portal = portal_for(request)
        path = request.path_info

        if portal == 'store':
            if not any(path.startswith(p) for p in self.STORE_PREFIXES):
                return redirect('/store/login/')

        elif portal == 'erp':
            if path.startswith('/store/'):
                return redirect('/login/')
            if (request.user.is_authenticated
                    and not any(path.startswith(p) for p in self.ERP_EXEMPT)
                    and getattr(request.user, 'role', None) != 'admin'):
                return redirect('/login/')

        return self.get_response(request)
