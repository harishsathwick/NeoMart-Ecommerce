from .models import Category, CartItem
from decimal import Decimal

def theme_context(request):
    theme = request.session.get('theme', 'light')
    return {'current_theme': theme}

def category_context(request):
    try:
        categories = Category.objects.all()
    except Exception:
        categories = []
    return {'nav_categories': categories}

def cart_context(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user).select_related('product')
        total = sum(item.subtotal for item in items) or Decimal('0.00')
        count = sum(item.quantity for item in items) or 0
    else:
        items = []
        total = Decimal('0.00')
        count = 0

    return {
        'mini_cart_items': items,
        'mini_cart_total': total,
        'mini_cart_count': count,
    }