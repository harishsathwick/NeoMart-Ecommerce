from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import logout_view

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('category/<slug:slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),

    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('login/', auth_views.LoginView.as_view(template_name='shop/login.html'), name='login'),
    path("logout/", logout_view, name="logout"),
    path('register/', views.register, name='register'),

    path('set-theme/<str:theme>/', views.set_theme, name='set_theme'),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<int:product_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),
    path('compare/', views.compare_view, name='compare_view'),
    path('compare/add/<int:product_id>/', views.add_to_compare, name='add_to_compare'),
    path('compare/remove/<int:product_id>/', views.remove_from_compare, name='remove_from_compare'),



]

