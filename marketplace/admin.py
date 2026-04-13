from django.contrib import admin
from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'seller', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')
