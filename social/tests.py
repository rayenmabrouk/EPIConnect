from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user
from notifications.models import Notification
from social.models import Post
from wallet.models import Wallet


class LikeTests(TestCase):
    def setUp(self):
        self.author = make_user('author')
        self.fan = make_user('fan')
        self.post = Post.objects.create(author=self.author, content='How do I configure a VLAN?')

    def like(self, user):
        self.client.force_login(user)
        return self.client.post(reverse('social:like', args=[self.post.pk]))

    def test_like_toggle(self):
        self.assertTrue(self.like(self.fan).json()['liked'])
        self.assertFalse(self.like(self.fan).json()['liked'])

    def test_like_unlike_loop_rewards_only_once(self):
        # Regression: toggling used to mint 2 points + a notification every time.
        for _ in range(5):
            self.like(self.fan)
            self.like(self.fan)
        self.assertEqual(Wallet.objects.get(user=self.author).balance, 2)
        self.assertEqual(Notification.objects.filter(user=self.author, type='like').count(), 1)

    def test_unverified_user_cannot_like_or_comment(self):
        lurker = make_user('lurker', verified=False)
        self.assertEqual(self.like(lurker).status_code, 403)
        response = self.client.post(reverse('social:comment', args=[self.post.pk]), {'content': 'hi'})
        self.assertEqual(response.status_code, 403)


class PostTests(TestCase):
    def test_create_post_awards_point_and_badge(self):
        user = make_user('poster')
        self.client.force_login(user)
        response = self.client.post(reverse('social:create'), {'content': 'First!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Wallet.objects.get(user=user).balance, 1)
        self.assertTrue(user.badges.filter(badge_type='first_post').exists())

    def test_anonymous_post_hides_author(self):
        user = make_user('shy')
        post = Post.objects.create(author=user, content='secret question', is_anonymous=True)
        html = self.client.get(reverse('social:detail', args=[post.pk])).content.decode()
        self.assertIn('Anonymous', html)
        self.assertNotIn(reverse('users:profile', args=[user.pk]), html)

    def test_only_author_can_delete(self):
        owner, other = make_user('owner'), make_user('other')
        post = Post.objects.create(author=owner, content='mine')
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('social:delete', args=[post.pk])).status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_post_creation_is_rate_limited(self):
        user = make_user('spammer')
        self.client.force_login(user)
        codes = [self.client.post(reverse('social:create'), {'content': f'spam {i}'}).status_code for i in range(7)]
        self.assertEqual(codes[:5], [302] * 5)
        self.assertEqual(codes[5], 429)
