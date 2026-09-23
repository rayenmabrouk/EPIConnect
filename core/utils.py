"""Shared helpers used across apps."""


def get_client_ip(request):
    """Return the real client IP address.

    In production Gunicorn listens on 127.0.0.1 only and sits behind Nginx,
    so REMOTE_ADDR is always 127.0.0.1. Nginx overwrites ``X-Real-IP`` with
    ``$remote_addr`` (see deploy/nginx/epiconnect.conf), so that header can be
    trusted. ``X-Forwarded-For`` is NOT used: its first value is supplied by
    the client and can be spoofed to evade rate limiting / lockouts.

    Used by the audit log, django-axes (AXES_CLIENT_IP_CALLABLE) and
    django-ratelimit (RATELIMIT_IP_META_KEY).
    """
    if request is None:
        return None
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or None
