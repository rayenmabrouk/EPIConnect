from django.contrib.auth.mixins import LoginRequiredMixin
from users.mixins import VerifiedStudentMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, CreateView
from django.contrib import messages as django_messages

from .models import Post, Comment, Like
from .forms import PostForm, CommentForm
from notifications.models import Notification


class FeedView(ListView):
    model = Post
    template_name = 'social/feed.html'
    context_object_name = 'posts'
    paginate_by = 15

    def get_queryset(self):
        qs = Post.objects.select_related('author').annotate(
            comments_count=Count('comments'),
            likes_count=Count('likes'),
        )
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                user_liked=Exists(
                    Like.objects.filter(user=self.request.user, post=OuterRef('pk'))
                )
            )
        return qs.order_by('-created_at')


class PostCreateView(VerifiedStudentMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'social/post_form.html'

    def form_valid(self, form):
        post = form.save(commit=False)
        post.author = self.request.user
        post.save()
        from wallet.utils import award_points, award_badge
        award_points(self.request.user, 1, 'Published a Help Wall post')
        # First post badge
        if Post.objects.filter(author=self.request.user).count() == 1:
            award_badge(self.request.user, 'first_post')
        django_messages.success(self.request, 'Post published! +1 EPI-point earned.')
        return redirect(reverse('social:detail', kwargs={'pk': post.pk}))


class PostDetailView(View):
    def get(self, request, pk):
        post = get_object_or_404(
            Post.objects.select_related('author').annotate(
                likes_count=Count('likes'),
            ),
            pk=pk,
        )
        comments = post.comments.select_related('author').order_by('created_at')
        user_liked = False
        if request.user.is_authenticated:
            user_liked = Like.objects.filter(user=request.user, post=post).exists()

        comment_form = CommentForm()
        return render(request, 'social/post_detail.html', {
            'post': post,
            'comments': comments,
            'user_liked': user_liked,
            'comment_form': comment_form,
        })


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()

            # Notify the post author (unless they're commenting on their own post)
            if post.author != request.user:
                commenter_name = 'Someone' if comment.is_anonymous else request.user.username
                Notification.objects.create(
                    user=post.author,
                    type='comment',
                    content=f"{commenter_name} commented on your post",
                    link=f"/social/{post.pk}/",
                )

            django_messages.success(request, 'Comment added!')
            from wallet.utils import award_points, award_badge
            award_points(request.user, 2, 'Left a comment on Help Wall')
            # Active helper badge: 10+ comments
            if Comment.objects.filter(author=request.user).count() >= 10:
                award_badge(request.user, 'active_helper')
            if post.author != request.user:
                award_points(post.author, 3, 'Someone commented on your post')
                # Top tutor badge: 10+ total likes on own posts
                total_likes = Like.objects.filter(post__author=post.author).count()
                if total_likes >= 10:
                    award_badge(post.author, 'top_tutor')
        return redirect(reverse('social:detail', kwargs={'pk': pk}))


class PostDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if request.user != post.author:
            raise PermissionDenied
        post.delete()
        django_messages.success(request, 'Post deleted.')
        return redirect(reverse('social:feed'))


class CommentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if request.user != comment.author:
            raise PermissionDenied
        post_pk = comment.post_id
        comment.delete()
        django_messages.success(request, 'Comment deleted.')
        return redirect(reverse('social:detail', kwargs={'pk': post_pk}))


class LikeToggleView(LoginRequiredMixin, View):
    """AJAX toggle like on a post."""

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, post=post)

        if not created:
            like.delete()
            liked = False
        else:
            liked = True
            # Notify post author on like (not on unlike)
            if post.author != request.user:
                Notification.objects.create(
                    user=post.author,
                    type='like',
                    content=f"{request.user.username} liked your post",
                    link=f"/social/{post.pk}/",
                )
                from wallet.utils import award_points, award_badge
                award_points(post.author, 2, f'{request.user.username} liked your post')
                # Top tutor badge: 10+ total likes on own posts
                total_likes = Like.objects.filter(post__author=post.author).count()
                if total_likes >= 10:
                    award_badge(post.author, 'top_tutor')

        return JsonResponse({
            'liked': liked,
            'count': post.likes.count(),
        })
