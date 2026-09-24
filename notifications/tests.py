from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user
from notifications.models import Notification


class NotificationTests(TestCase):
    def test_user_only_sees_own_notifications(self):
        alice, bob = make_user('alice'), make_user('bob')
        n = Notification.objects.create(user=alice, type='alert', content='<b>x</b>', link='/social/')
        self.client.force_login(bob)
        self.assertEqual(self.client.get(reverse('notifications:read', args=[n.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('notifications:dropdown')).json()['notifications'], [])

    def test_mark_all_read(self):
        alice = make_user('alice')
        Notification.objects.create(user=alice, type='alert', content='a')
        self.client.force_login(alice)
        self.client.post(reverse('notifications:mark_all_read'))
        self.assertFalse(Notification.objects.filter(is_read=False).exists())

    def test_external_link_is_not_followed(self):
        alice = make_user('alice')
        n = Notification.objects.create(user=alice, type='alert', content='x', link='https://evil.example/phish')
        self.client.force_login(alice)
        response = self.client.get(reverse('notifications:read', args=[n.pk]))
        self.assertEqual(response['Location'], reverse('notifications:list'))
