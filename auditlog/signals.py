from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .utils import log_action, get_client_ip
from .models import AuditLog


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action='login',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        details=f'Successful login',
    )


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action='logout',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        details='User logged out',
    )


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    AuditLog.objects.create(
        user=None,
        action='login_failed',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        details=f'Failed login attempt for username: {credentials.get("username", "unknown")}',
    )

