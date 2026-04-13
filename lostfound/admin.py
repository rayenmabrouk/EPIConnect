from django.contrib import admin
from .models import Item, ItemHistory


class ItemHistoryInline(admin.TabularInline):
    model = ItemHistory
    extra = 0
    readonly_fields = ('action', 'details', 'user', 'timestamp')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'location', 'owner', 'finder', 'date', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('title', 'description', 'location')
    inlines = [ItemHistoryInline]


@admin.register(ItemHistory)
class ItemHistoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'action', 'user', 'timestamp')
    list_filter = ('action',)
