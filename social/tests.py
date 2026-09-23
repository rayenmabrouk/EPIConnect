from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification
from social.models import Post
from users.models import StudentProfile, User
from wallet.models import Wallet


def verified(username):
    user = User.objects.create_user(username, f'{username}@epi.tn', 'Str0ng-Passw0rd!')
    StudentProfile.objects.filter(user=user).update(is_verified=True)
    return user


class HelpWallTests(TestCase):
    def setUp(self):
        self.author = verified('author')
        self.fan = verified('fan')
        self.post = Post.objects.create(author=self.author, content='Need help with Terraform')

    def balance(self, user):
        return Wallet.objects.get_or_create(user=user)[0].balance

    def test_create_post_awards_point_and_first_post_badge(self):
        self.client.force_login(self.fan)
        self.client.post(reverse('social:create'), {'content': 'Hello'})
        self.assertEqual(self.balance(self.fan), 1)
        self.assertTrue(self.fan.badges.filter(badge_type='first_post').exists())

    def test_like_toggle_cannot_farm_points(self):
        self.client.force_login(self.fan)
        url = reverse('social:like', args=[self.post.pk])
        for _ in range(5):          # like, unlike, like, unlike, like
            self.client.post(url)
        self.assertEqual(self.balance(self.author), 2)
        self.assertEqual(Notification.objects.filter(user=self.author, type='like').count(), 1)
        self.assertEqual(self.post.likes.count(), 1)

    def test_unverified_user_cannot_comment(self):
        lurker = User.objects.create_user('lurker', 'l@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(lurker)
        resp = self.client.post(reverse('social:comment', args=[self.post.pk]), {'content': 'hi'})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.post.comments.count(), 0)

    def test_comment_notifies_author(self):
        self.client.force_login(self.fan)
        self.client.post(reverse('social:comment', args=[self.post.pk]), {'content': 'Try modules'})
        self.assertEqual(self.post.comments.count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.author, type='comment').exists())

    def test_anonymous_post_hides_author_on_feed(self):
        Post.objects.create(author=self.author, content='secret question', is_anonymous=True)
        resp = self.client.get(reverse('social:feed'))
        self.assertContains(resp, 'Anonymous')

    def test_only_author_can_delete(self):
        self.client.force_login(self.fan)
        resp = self.client.post(reverse('social:delete', args=[self.post.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())
