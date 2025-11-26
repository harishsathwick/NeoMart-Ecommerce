import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, Sum, F
from .models import Product, Category, CartItem, Order, OrderItem, Address, Wishlist, ProductVariant, VariantType, Review
from .forms import RegisterForm, AddressForm, ReviewForm
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.db.models import Avg
from .models import VariantType

def _push_recently_viewed(request, product_id, max_items=8):
    """
    Store recently viewed product IDs in session (most recent first).
    """
    rv = request.session.get('recently_viewed', [])
    if product_id in rv:
        rv.remove(product_id)
    rv.insert(0, product_id)
    rv = rv[:max_items]
    request.session['recently_viewed'] = rv



def home(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(short_description__icontains=query) |
            Q(description__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    hot_deals = products.filter(is_hot_deal=True)[:8]
    top_deals = products.filter(is_top_deal=True)[:8]
    latest_products = products.order_by('-created_at')[:12]
    recent_ids = request.session.get('recently_viewed', [])
    recent_products_qs = Product.objects.filter(id__in=recent_ids)
    recent_products = list(recent_products_qs)
    recent_products.sort(key=lambda p: recent_ids.index(p.id))
    recently_viewed_products = recent_products[:8]


    context = {
        'hot_deals': hot_deals,
        'top_deals': top_deals,
        'latest_products': latest_products,
        'recently_viewed_products': recently_viewed_products,
    }
    return render(request, 'shop/home.html', context)

def product_list(request, slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.all()

    if slug:
        category = get_object_or_404(Category, slug=slug)
        products = products.filter(category=category)

    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(short_description__icontains=query) |
            Q(description__icontains=query)
        )

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Wishlist IDs for current user (for filled heart icon)
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list("product_id", flat=True)
        )

    context = {
        'category': category,
        'categories': categories,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'wishlist_ids': wishlist_ids,   # ✅ sent to template
    }
    return render(request, 'shop/product_list.html', context)


@login_required(login_url='login')
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    extra_images = product.images.all()

    reviews = Review.objects.filter(product=product).order_by('-created_at')
    recommended = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            user_has_reviewed = Review.objects.filter(user=request.user, product=product).exists()
            if user_has_reviewed:
                messages.error(request, "You have already reviewed this product.")
            else:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                messages.success(request, "Review submitted successfully!")
            return redirect('product_detail', slug=slug)
    else:
        form = ReviewForm()

    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    # ---------------- RECENTLY VIEWED ----------------
    _push_recently_viewed(request, product.id)

    recent_ids = request.session.get('recently_viewed', [])
    recent_products_qs = Product.objects.filter(id__in=recent_ids).exclude(id=product.id)
    recent_products = list(recent_products_qs)
    recent_products.sort(key=lambda p: recent_ids.index(p.id))
    recently_viewed_products = recent_products[:8]

    # ---------------- VARIANTS ----------------
    variants = product.variants.select_related("variant_type").all().order_by("variant_type__name")
    variant_types = VariantType.objects.filter(productvariant__product=product).distinct()

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'recommended_products': recommended,
        'reviews': reviews,
        'form': form,
        'avg_rating': round(avg_rating, 1),
        'extra_images': extra_images,
        'variants': variants,
        'variant_types': variant_types,
        'recently_viewed_products': recently_viewed_products,
    })

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant = None

    variant_id = request.GET.get('variant')
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant
    )
    if not created:
        cart_item.quantity += 1
    cart_item.save()

    messages.success(request, f"Added {product.name} to your cart.")
    return redirect('cart')


@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)

    # Base subtotal and item count
    subtotal = sum(item.subtotal for item in cart_items) or Decimal('0.00')
    total_items = sum(item.quantity for item in cart_items) or 0

    # Old bulk discount logic (20% if more than 5 items)
    bulk_discount = Decimal('0.00')
    if total_items > 5:
        bulk_discount = (subtotal * Decimal('0.20')).quantize(Decimal('0.01'))

    # Handle coupon apply/clear (via modal form)
    coupon_code = request.session.get('coupon_code', '')
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip().upper()
        if code:
            valid_codes = ['NEO10', 'FLAT100']
            if code in valid_codes:
                request.session['coupon_code'] = code
                coupon_code = code
                messages.success(request, f"Coupon {code} applied.")
            else:
                request.session.pop('coupon_code', None)
                coupon_code = ''
                messages.error(request, "Invalid coupon code.")
        else:
            # Empty input clears coupon
            request.session.pop('coupon_code', None)
            coupon_code = ''
            messages.info(request, "Coupon removed.")
        return redirect('cart')

    # Amount after bulk discount
    amount_after_bulk = subtotal - bulk_discount
    if amount_after_bulk < 0:
        amount_after_bulk = Decimal('0.00')

    # Coupon discount logic
    coupon_discount = Decimal('0.00')
    if coupon_code == 'NEO10':
        coupon_discount = (amount_after_bulk * Decimal('0.10')).quantize(Decimal('0.01'))
    elif coupon_code == 'FLAT100':
        coupon_discount = Decimal('100.00')
        if coupon_discount > amount_after_bulk:
            coupon_discount = amount_after_bulk

    # Amount after coupon (before GST)
    total_before_gst = amount_after_bulk - coupon_discount
    if total_before_gst < 0:
        total_before_gst = Decimal('0.00')

    # Simple GST placeholder (18%)
    gst_estimate = (total_before_gst * Decimal('0.18')).quantize(Decimal('0.01'))

    # Final total including GST
    grand_total = total_before_gst + gst_estimate

    # Delivery estimate: today + 3 to 5 days
    today = date.today()
    start = today + timedelta(days=3)
    end = today + timedelta(days=5)
    estimated_delivery = f"{start.strftime('%d %b')} – {end.strftime('%d %b')}"

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'bulk_discount': bulk_discount,
        'coupon_discount': coupon_discount,
        'gst_estimate': gst_estimate,
        'total': grand_total,
        'total_items': total_items,
        'coupon_code': coupon_code,
        'estimated_delivery': estimated_delivery,
    }
    return render(request, 'shop/cart.html', context)

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect('cart')

@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        if qty <= 0:
            item.delete()
        else:
            item.quantity = qty
            item.save()
    return redirect('cart')

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('product_list')

    # Compute totals in Python
    total = sum(item.subtotal for item in cart_items) or Decimal('0.00')
    bulk_discount = Decimal('0.00')
    total_items = sum(item.quantity for item in cart_items) or 0

    if total_items > 5:
        bulk_discount = total * Decimal('0.20')
        total -= bulk_discount

    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.is_default = True
            address.save()

            order_id = uuid.uuid4().hex[:10].upper()
            order = Order.objects.create(
                user=request.user,
                address=address,
                order_id=order_id,
                total_amount=total,
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                )
                # reduce stock
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save()
            cart_items.delete()
            messages.success(request, f"Order {order.order_id} placed successfully!")
            return redirect('order_success', order_id=order.order_id)

    else:
        # prefill with default address if exists
        default_address = Address.objects.filter(user=request.user, is_default=True).first()
        initial = {}
        if default_address:
            initial = {
                'full_name': default_address.full_name,
                'address_line': default_address.address_line,
                'flat_house_no': default_address.flat_house_no,
                'landmark': default_address.landmark,
                'phone': default_address.phone,
                'email': default_address.email,
                'pincode': default_address.pincode,
            }
        form = AddressForm(initial=initial)

    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'bulk_discount': bulk_discount,
        'total_items': total_items,
        'form': form,
    })

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/my_orders.html', {'orders': orders})

@login_required
def dashboard(request):
    orders_qs = Order.objects.filter(user=request.user).order_by('-created_at')
    addresses = Address.objects.filter(user=request.user)

    total_spent = orders_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_orders = orders_qs.count()
    delivered_orders = orders_qs.filter(status='delivered').count() if hasattr(Order, 'status') else 0
    pending_orders = orders_qs.exclude(status='delivered').count() if hasattr(Order, 'status') else total_orders

    last_order = orders_qs.first()
    last_order_date = last_order.created_at if last_order else None

    recent_orders = orders_qs[:5]

    context = {
        'orders': recent_orders,
        'addresses': addresses,
        'total_spent': total_spent,
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'last_order_date': last_order_date,
    }
    return render(request, 'shop/dashboard.html', context)


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. You can now log in.")
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'shop/register.html', {'form': form})

def set_theme(request, theme):
    if theme in ['light', 'dark', 'gradient']:
        request.session['theme'] = theme
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required(login_url='login')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "Added to wishlist ❤️")
    return redirect(request.META.get("HTTP_REFERER", "product_list"))

@login_required(login_url='login')
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user)
    return render(request, "shop/wishlist.html", {"items": items})

@login_required(login_url='login')
def remove_from_wishlist(request, product_id):
    item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
    item.delete()
    messages.success(request, "Removed from wishlist ❌")
    return redirect("wishlist")

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Reuse delivery estimate logic (3–5 days from today)
    today = date.today()
    start = today + timedelta(days=3)
    end = today + timedelta(days=5)
    estimated_delivery = f"{start.strftime('%d %b')} – {end.strftime('%d %b')}"

    return render(request, 'shop/order_success.html', {
        'order': order,
        'estimated_delivery': estimated_delivery,
    })



def _get_compare_list(request):
    return request.session.get('compare_list', [])

def _save_compare_list(request, compare_list):
    request.session['compare_list'] = compare_list

@require_POST
def add_to_compare(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    compare = _get_compare_list(request)
    if product_id not in compare:
        # limit to max 4 items
        if len(compare) >= 4:
            compare.pop(0)
        compare.append(product_id)
        _save_compare_list(request, compare)
        messages.success(request, f"Added {product.name} to compare.")
    else:
        messages.info(request, "Product already in compare list.")
    return redirect(request.META.get("HTTP_REFERER", "product_list"))

@require_POST
def remove_from_compare(request, product_id):
    compare = _get_compare_list(request)
    if product_id in compare:
        compare.remove(product_id)
        _save_compare_list(request, compare)
        messages.info(request, "Removed from compare.")
    return redirect('compare_view')

def compare_view(request):
    compare = _get_compare_list(request)
    products_qs = Product.objects.filter(id__in=compare)
    products = list(products_qs)
    products.sort(key=lambda p: compare.index(p.id))
    return render(request, 'shop/compare.html', {'products': products})
