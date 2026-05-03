from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('login_failed', 'Login Failed'),
        ('register', 'Register'),
        ('profile_update', 'Profile Update'),
        ('item_create', 'Item Created'),
        ('item_update', 'Item Updated'),
        ('item_delete', 'Item Deleted'),
        ('listing_create', 'Listing Created'),
        ('listing_update', 'Listing Updated'),
        ('listing_delete', 'Listing Deleted'),
        ('post_create', 'Post Created'),
        ('post_delete', 'Post Deleted'),
        ('message_send', 'Message Sent'),
        ('account_locked', 'Account Locked'),
        ('password_change', 'Password Changed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user = self.user.username if self.user else 'Anonymous'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {user} — {self.get_action_display()}'
