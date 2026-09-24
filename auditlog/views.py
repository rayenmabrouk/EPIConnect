from datetime import timedelta

from axes.models import AccessAttempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .models import AuditLog


@login_required
def security_dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    recent_logs = AuditLog.objects.select_related('user').all()[:50]

    total_logins = AuditLog.objects.filter(action='login', timestamp__gte=last_24h).count()
    failed_logins = AuditLog.objects.filter(action='login_failed', timestamp__gte=last_24h).count()
    new_registers = AuditLog.objects.filter(action='register', timestamp__gte=last_7d).count()
    locked_accounts = AccessAttempt.objects.filter(failures_since_start__gte=5).count()

    access_attempts = AccessAttempt.objects.order_by('-attempt_time')[:20]

    actions = dict(
        AuditLog.objects.filter(timestamp__gte=last_7d)
        .values_list('action')
        .annotate(n=Count('id'))
        .values_list('action', 'n')
    )

    return render(request, 'auditlog/dashboard.html', {
        'recent_logs': recent_logs,
        'total_logins': total_logins,
        'failed_logins': failed_logins,
        'new_registers': new_registers,
        'locked_accounts': locked_accounts,
        'access_attempts': access_attempts,
        'actions': actions,
    })
