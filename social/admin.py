from django.contrib import admin
from .models import Post, Comment, Like


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'content', 'is_anonymous', 'created_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'author', 'is_anonymous', 'content_preview', 'created_at')
    list_filter = ('is_anonymous', 'created_at')
    inlines = [CommentInline]

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'post', 'author', 'is_anonymous', 'created_at')
    list_filter = ('is_anonymous',)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post')
