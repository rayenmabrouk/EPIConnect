from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'ip_address', 'details']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'ip_address', 'details']
    readonly_fields = ['user', 'action', 'ip_address', 'user_agent', 'details', 'timestamp']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
