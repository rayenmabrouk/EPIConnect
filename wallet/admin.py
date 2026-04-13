from django.contrib import admin
from .models import Wallet, Transaction, Perk, Redemption


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'created_at']
    search_fields = ['user__username']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'description', 'created_at']
    list_filter = ['type']


@admin.register(Perk)
class PerkAdmin(admin.ModelAdmin):
    list_display = ['title', 'cost', 'icon', 'is_active', 'stock']
    list_editable = ['is_active', 'cost', 'stock']


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'perk', 'points_spent', 'status', 'redeemed_at']
    list_filter = ['status']
    list_editable = ['status']
