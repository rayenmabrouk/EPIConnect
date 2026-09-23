from axes.signals import user_locked_out
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .utils import log_action


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_action(request, 'login', user=user, details='Successful login')


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    log_action(request, 'logout', user=user, details='User logged out')


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    username = (credentials or {}).get('username', 'unknown')
    log_action(request, 'login_failed', user=None,
               details=f'Failed login attempt for username: {username}')


@receiver(user_locked_out)
def on_locked_out(sender, request, username, ip_address, **kwargs):
    log_action(request, 'account_locked', user=None,
               details=f'Locked out after repeated failures: username={username}, ip={ip_address}')
