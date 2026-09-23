from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from lostfound.models import Item
        from marketplace.models import Listing
        from social.models import Post
        from users.models import User

        # Stats
        context['total_lost_items'] = Item.objects.filter(status='lost').count()
        context['total_found_items'] = Item.objects.filter(status='found').count()
        context['total_claimed_items'] = Item.objects.filter(status='claimed').count()
        context['total_listings'] = Listing.objects.count()
        context['total_posts'] = Post.objects.count()
        context['total_users'] = User.objects.count()

        # Recent activity
        context['latest_items'] = (
            Item.objects.select_related('owner')
            .order_by('-created_at')[:5]
        )
        context['latest_listings'] = (
            Listing.objects.select_related('seller')
            .order_by('-created_at')[:5]
        )
        context['latest_posts'] = (
            Post.objects.select_related('author')
            .order_by('-created_at')[:5]
        )
        return context


def healthz(request):
    """Liveness + DB check, used by the Jenkins 'Verify Deployment' stage."""
    from django.db import connection
    from django.http import JsonResponse
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:  # pragma: no cover - only on DB outage
        return JsonResponse({'status': 'db_unavailable'}, status=503)


def metrics(request):
    """Prometheus scrape endpoint (django_http_*, django_db_*, django_cache_*).

    Only reachable by Prometheus on the VM itself, which scrapes Gunicorn
    directly on 127.0.0.1:8000. Anything that came through Nginx carries an
    X-Real-IP header and is refused (Nginx also denies /metrics).
    """
    from django.http import HttpResponseForbidden
    from django_prometheus.exports import ExportToDjangoView
    if request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1') or 'HTTP_X_REAL_IP' in request.META:
        return HttpResponseForbidden('Forbidden')
    return ExportToDjangoView(request)
