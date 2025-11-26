from django.contrib import admin
from .models import (
    Category, Product, Address, Order, OrderItem, CartItem,
    UserProfile, Wishlist, Review, ProductImage, ProductVariant, VariantType
)

# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug')


# Inline for Product Images
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2


# Inline for Product Variant
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_hot_deal', 'is_top_deal')
    list_filter = ('category', 'is_hot_deal', 'is_top_deal')
    search_fields = ('name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]


admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(CartItem)
admin.site.register(UserProfile)
admin.site.register(Wishlist)
admin.site.register(Review)
admin.site.register(VariantType)
