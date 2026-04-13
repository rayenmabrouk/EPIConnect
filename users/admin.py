from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe
from .models import User, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'student_id', 'verification_badge', 'created_at']
    list_filter = ['is_verified']
    search_fields = ['user__username', 'user__email', 'student_id']
    actions = ['verify_students', 'unverify_students']

    @admin.display(description='Status')
    def verification_badge(self, obj):
        if obj.is_verified:
            return mark_safe('<span style="color:green;font-weight:bold;">&#10004; Verified</span>')
        return mark_safe('<span style="color:orange;font-weight:bold;">&#9203; Pending</span>')

    @admin.action(description='✔ Verify selected students')
    def verify_students(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} student(s) verified.')

    @admin.action(description='✘ Unverify selected students')
    def unverify_students(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} student(s) unverified.')


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    fields = ['student_id', 'is_verified', 'bio', 'profile_picture']
    readonly_fields = ['student_id']


class CustomUserAdmin(UserAdmin):
    inlines = [StudentProfileInline]
    list_display = ['username', 'email', 'get_student_id', 'get_verified', 'is_staff']

    @admin.display(description='Student ID')
    def get_student_id(self, obj):
        return getattr(obj, 'profile', None) and obj.profile.student_id or '—'

    @admin.display(description='Verified', boolean=True)
    def get_verified(self, obj):
        return getattr(obj, 'profile', None) and obj.profile.is_verified


admin.site.register(User, CustomUserAdmin)
