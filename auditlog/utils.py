from core.utils import get_client_ip  # noqa: F401  (re-exported for existing imports)

from .models import AuditLog


def get_user_agent(request):
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:500]


def log_action(request, action, user=None, details=''):
    if user is None and request is not None and request.user.is_authenticated:
        user = request.user
    AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=details[:1000],
    )
