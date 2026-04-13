from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Max, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from .models import Conversation, Message
from users.models import User


class InboxView(LoginRequiredMixin, ListView):
    template_name = 'messaging/conversation_list.html'
    context_object_name = 'conversations'

    def get_queryset(self):
        return (
            Conversation.objects
            .filter(participants=self.request.user)
            .annotate(last_msg_time=Max('messages__timestamp'))
            .order_by('-last_msg_time')
            .prefetch_related('participants', 'messages')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        conv_data = []
        for conv in ctx['conversations']:
            other = conv.participants.exclude(pk=user.pk).first()
            last_msg = conv.last_message
            unread = conv.messages.filter(is_read=False).exclude(sender=user).count()
            conv_data.append({
                'conversation': conv,
                'other_user': other,
                'last_message': last_msg,
                'unread_count': unread,
            })
        ctx['conv_data'] = conv_data
        return ctx


class ConversationDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.participants.filter(pk=request.user.pk).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        # Mark unread messages as read
        conversation.messages.filter(is_read=False).exclude(
            sender=request.user
        ).update(is_read=True)

        messages_qs = conversation.messages.select_related('sender').order_by('timestamp')
        other_user = conversation.participants.exclude(pk=request.user.pk).first()

        from django.shortcuts import render
        return render(request, 'messaging/conversation_detail.html', {
            'conversation': conversation,
            'chat_messages': messages_qs,
            'other_user': other_user,
        })


class StartConversationView(LoginRequiredMixin, View):
    """Create or get a conversation with another user, then redirect to it."""

    def get(self, request):
        other_user_pk = request.GET.get('user')
        if not other_user_pk:
            return redirect('messaging:inbox')

        other_user = get_object_or_404(User, pk=other_user_pk)
        if other_user == request.user:
            return redirect('messaging:inbox')

        # Find existing conversation between these two users
        conversation = (
            Conversation.objects
            .filter(participants=request.user)
            .filter(participants=other_user)
            .first()
        )

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)

        return redirect('messaging:detail', pk=conversation.pk)


class SendMessageView(LoginRequiredMixin, View):
    """AJAX endpoint: send a message to a conversation."""

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.participants.filter(pk=request.user.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')

        if not content and not image:
            return JsonResponse({'error': 'Empty message'}, status=400)

        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            image=image,
        )

        # Update conversation timestamp
        conversation.save()

        # Create notification for the other participant(s)
        from notifications.models import Notification
        recipients = conversation.participants.exclude(pk=request.user.pk)
        for recipient in recipients:
            Notification.objects.create(
                user=recipient,
                type='message',
                content=f"New message from {request.user.username}",
                link=f"/messaging/{conversation.pk}/",
            )

        return JsonResponse({
            'id': msg.pk,
            'content': msg.content,
            'image_url': msg.image.url if msg.image else None,
            'sender': msg.sender.username,
            'sender_id': msg.sender.pk,
            'timestamp': msg.timestamp.strftime('%b %d, %H:%M'),
            'is_mine': True,
        })


class FetchMessagesView(LoginRequiredMixin, View):
    """AJAX endpoint: fetch messages after a given message ID."""

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not conversation.participants.filter(pk=request.user.pk).exists():
            return JsonResponse({'error': 'Forbidden'}, status=403)

        after_id = request.GET.get('after', 0)
        try:
            after_id = int(after_id)
        except (ValueError, TypeError):
            after_id = 0

        new_messages = (
            conversation.messages
            .filter(pk__gt=after_id)
            .select_related('sender')
            .order_by('timestamp')
        )

        # Mark incoming messages as read
        new_messages.filter(is_read=False).exclude(
            sender=request.user
        ).update(is_read=True)

        data = []
        for msg in new_messages:
            data.append({
                'id': msg.pk,
                'content': msg.content,
                'image_url': msg.image.url if msg.image else None,
                'sender': msg.sender.username,
                'sender_id': msg.sender.pk,
                'timestamp': msg.timestamp.strftime('%b %d, %H:%M'),
                'is_mine': msg.sender == request.user,
            })

        return JsonResponse({'messages': data})
