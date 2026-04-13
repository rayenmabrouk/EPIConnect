from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from users.mixins import VerifiedStudentMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages

from .models import Item, ItemHistory
from .forms import ItemForm, ItemFilterForm


class ItemListView(ListView):
    model = Item
    template_name = 'lostfound/item_list.html'
    context_object_name = 'items'
    paginate_by = 12

    def get_queryset(self):
        qs = Item.objects.select_related('owner', 'finder')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = ItemFilterForm(self.request.GET)
        ctx['total'] = self.get_queryset().count()
        return ctx


class ItemDetailView(DetailView):
    model = Item
    template_name = 'lostfound/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return Item.objects.select_related('owner', 'finder')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['timeline'] = self.object.history.select_related('user').order_by('timestamp')
        ctx['can_edit'] = self._can_edit()
        return ctx

    def _can_edit(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        item = self.object
        return user == item.owner or user == item.finder


class ItemCreateView(VerifiedStudentMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'lostfound/item_form.html'

    def form_valid(self, form):
        item = form.save(commit=False)
        item_type = form.cleaned_data['item_type']

        if item_type == 'lost':
            item.status = 'lost'
            item.owner = self.request.user
        else:
            item.status = 'found'
            item.finder = self.request.user
            item.owner = self.request.user

        item.save()

        ItemHistory.objects.create(
            item=item,
            action='created',
            details=f"Item reported as {item.get_status_display().lower()} by {self.request.user.username}",
            user=self.request.user,
        )

        from wallet.utils import award_points
        award_points(self.request.user, 5, f'Reported a {item_type} item: {item.title}')

        messages.success(self.request, 'Item reported successfully! +5 EPI-points earned.')
        return redirect(reverse('lostfound:detail', kwargs={'pk': item.pk}))


class ItemDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        if request.user != item.owner and request.user != item.finder:
            raise PermissionDenied
        item.delete()
        messages.success(request, 'Item deleted.')
        return redirect(reverse('lostfound:list'))


class ItemStatusUpdateView(LoginRequiredMixin, View):
    VALID_TRANSITIONS = {
        'lost': ['found', 'archived'],
        'found': ['claimed', 'archived'],
        'claimed': ['found', 'lost', 'archived'],
        'archived': ['lost', 'found'],
    }

    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)

        if request.user != item.owner and request.user != item.finder:
            raise PermissionDenied

        new_status = request.POST.get('status')
        allowed = self.VALID_TRANSITIONS.get(item.status, [])
        if new_status not in allowed:
            messages.error(request, f"Cannot change status from {item.get_status_display()} to {new_status}.")
            return redirect(reverse('lostfound:detail', kwargs={'pk': pk}))

        old_status = item.get_status_display()
        item.status = new_status
        item.save()

        ItemHistory.objects.create(
            item=item,
            action='status_changed',
            details=f"Status changed from {old_status} to {item.get_status_display()} by {request.user.username}",
            user=request.user,
        )

        # Notify owner/finder about the status change
        from notifications.models import Notification
        notify_users = set()
        if item.owner and item.owner != request.user:
            notify_users.add(item.owner)
        if item.finder and item.finder != request.user:
            notify_users.add(item.finder)
        for recipient in notify_users:
            Notification.objects.create(
                user=recipient,
                type='alert',
                content=f'"{item.title}" has been marked as {item.get_status_display().lower()}',
                link=f"/lostfound/{item.pk}/",
            )

        # Award points and badges for resolving an item
        from wallet.utils import award_points, award_badge
        if new_status == 'claimed':
            award_points(request.user, 15, f'Item "{item.title}" marked as claimed')
            award_badge(request.user, 'good_samaritan')
        elif new_status == 'found':
            award_points(request.user, 10, f'Item "{item.title}" marked as found')
            award_badge(request.user, 'good_samaritan')

        messages.success(request, f"Item marked as {item.get_status_display()}.")
        return redirect(reverse('lostfound:detail', kwargs={'pk': pk}))
