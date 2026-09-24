import logging

from .models import AuditLog

logger = logging.getLogger('epiconnect.audit')


def get_client_ip(request):
    """Client address. REMOTE_ADDR has already been resolved from the trusted
    proxy chain by core.middleware.TrustedProxyMiddleware, so X-Forwarded-For
    is deliberately NOT read here (its left-most value is client-controlled)."""
    return request.META.get('REMOTE_ADDR') or None


def record(request, action, user=None, details=''):
    """Persist an audit event and mirror it to the structured log stream.

    The database row feeds the in-app security dashboard; the log line reaches
    CloudWatch Logs, where metric filters and alarms can act on it.
    """
    ip = get_client_ip(request) if request is not None else None
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request is not None else ''
    entry = AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=ip,
        user_agent=user_agent,
        details=details,
    )
    logger.info(
        'audit %s', action,
        extra={
            'event': 'audit',
            'action': action,
            'user_id': user.pk if user else None,
            'client_ip': ip,
            'details': details,
        },
    )
    return entry


def log_action(request, action, user=None, details=''):
    if user is None and request is not None and request.user.is_authenticated:
        user = request.user
    return record(request, action, user=user, details=details)
