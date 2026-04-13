from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'content', 'timestamp', 'is_read')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('pk', 'created_at', 'updated_at')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'content_preview', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'
