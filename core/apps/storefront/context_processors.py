from .models import Cart


def cart_item_count(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'customer':
        try:
            count = Cart.objects.get(user=request.user).items.count()
        except Cart.DoesNotExist:
            count = 0
        return {'cart_item_count': count}
    return {'cart_item_count': 0}
