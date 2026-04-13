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
