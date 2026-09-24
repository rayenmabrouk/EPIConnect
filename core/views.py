from django.http import HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.templatetags.static import static
from django.views.generic import TemplateView


def ratelimited(request, exception=None):
    """Returned by django-ratelimit (RatelimitMiddleware) when a limit is hit."""
    message = 'Too many requests. Please slow down and try again in a minute.'
    if request.headers.get('X-CSRFToken') or request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'error': message}, status=429)
    return HttpResponse(message, status=429, content_type='text/plain')


def favicon(request):
    """Browsers request /favicon.ico on every page (including the admin)."""
    return HttpResponsePermanentRedirect(static('favicon.svg'))


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
