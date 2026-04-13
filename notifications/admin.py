from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'content_preview', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'
