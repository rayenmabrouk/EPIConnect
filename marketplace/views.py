from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from users.mixins import VerifiedStudentMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from auditlog.utils import log_action
from .models import Listing
from .forms import ListingForm, ListingFilterForm


class ListingListView(ListView):
    model = Listing
    template_name = 'marketplace/listing_list.html'
    context_object_name = 'listings'
    paginate_by = 12

    def get_queryset(self):
        qs = Listing.objects.select_related('seller')
        q = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        sort = self.request.GET.get('sort', '').strip()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(category=category)

        if sort == 'price_asc':
            qs = qs.order_by('price')
        elif sort == 'price_desc':
            qs = qs.order_by('-price')
        else:
            qs = qs.order_by('-created_at')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = ListingFilterForm(self.request.GET)
        ctx['total'] = self.get_queryset().count()
        return ctx


class ListingDetailView(DetailView):
    model = Listing
    template_name = 'marketplace/listing_detail.html'
    context_object_name = 'listing'

    def get_queryset(self):
        return Listing.objects.select_related('seller')


class ListingDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk)
        if request.user != listing.seller:
            raise PermissionDenied
        log_action(request, 'listing_delete', details=f'Listing #{listing.pk}: {listing.title}')
        listing.delete()
        messages.success(request, 'Listing deleted.')
        return redirect(reverse('marketplace:list'))


@method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True), name='post')
class ListingCreateView(VerifiedStudentMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = 'marketplace/listing_form.html'

    def form_valid(self, form):
        listing = form.save(commit=False)
        listing.seller = self.request.user
        listing.save()
        log_action(self.request, 'listing_create', details=f'Listing #{listing.pk}: {listing.title}')
        from wallet.utils import award_badge
        if Listing.objects.filter(seller=self.request.user).count() >= 3:
            award_badge(self.request.user, 'trustworthy_seller')
        messages.success(self.request, 'Listing created successfully!')
        return redirect(reverse('marketplace:detail', kwargs={'pk': listing.pk}))
