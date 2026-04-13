from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationReadView(LoginRequiredMixin, View):
    """Mark a single notification as read and redirect to its link."""

    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        if notification.link:
            return redirect(notification.link)
        return redirect('notifications:list')


class MarkAllReadView(LoginRequiredMixin, View):
    """Mark all notifications as read."""

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('notifications:list')


class NotificationDropdownView(LoginRequiredMixin, View):
    """AJAX endpoint: return latest unread notifications for the navbar dropdown."""

    def get(self, request):
        notifications = (
            Notification.objects
            .filter(user=request.user)
            .order_by('-created_at')[:10]
        )
        data = []
        for n in notifications:
            data.append({
                'id': n.pk,
                'type': n.type,
                'content': n.content,
                'link': f"/notifications/{n.pk}/read/",
                'is_read': n.is_read,
                'time': n.created_at.strftime('%b %d, %H:%M'),
            })
        return JsonResponse({'notifications': data})
