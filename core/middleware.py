"""Infrastructure-facing middleware.

Both classes sit at the very top of MIDDLEWARE so that everything below them
(SecurityMiddleware, axes, django-ratelimit, the audit log) sees a correct,
non-spoofable client address and so that load-balancer health checks never
reach host validation.
"""
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse


class HealthCheckMiddleware:
    """Answer /healthz/ and /readyz/ before ALLOWED_HOSTS validation.

    The ALB health checker connects to the task's private IP, so its Host
    header is an IP address that is not (and should not be) in ALLOWED_HOSTS.
    Short-circuiting here keeps ALLOWED_HOSTS strict for real traffic.

    /healthz/  liveness: the Python process is serving requests (no I/O).
    /readyz/   readiness: the database answers a trivial query.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/healthz/':
            return HttpResponse('ok', content_type='text/plain')
        if request.path == '/readyz/':
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
            except Exception:  # noqa: BLE001 - any DB failure means "not ready"
                return JsonResponse({'status': 'unavailable', 'database': 'error'}, status=503)
            return JsonResponse({'status': 'ok', 'database': 'ok'})
        return self.get_response(request)


class TrustedProxyMiddleware:
    """Replace REMOTE_ADDR with the real client IP taken from X-Forwarded-For.

    Only the right-most TRUSTED_PROXY_COUNT hops are trusted. Each trusted
    proxy appends the address it received the connection from, so with
    CloudFront -> ALB -> app (count = 2) the header ends with
    "<client>, <cloudfront edge>" and the client is the second entry from the
    right. Anything to the left of that was supplied by the client and is
    ignored, which is what makes the value non-spoofable.

    With TRUSTED_PROXY_COUNT = 0 (local development) the header is ignored.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.count = int(getattr(settings, 'TRUSTED_PROXY_COUNT', 0))

    def __call__(self, request):
        if self.count > 0:
            forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
            hops = [h.strip() for h in forwarded.split(',') if h.strip()]
            if len(hops) >= self.count:
                request.META['REMOTE_ADDR'] = hops[-self.count]
        return self.get_response(request)
