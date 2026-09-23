from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification
from users.models import User


class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(self.user)

    def test_read_marks_and_redirects_internal(self):
        n = Notification.objects.create(user=self.user, type='alert', content='x', link='/social/1/')
        resp = self.client.get(reverse('notifications:read', args=[n.pk]))
        self.assertRedirects(resp, '/social/1/', fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_external_link_not_followed(self):
        n = Notification.objects.create(user=self.user, type='alert', content='x', link='https://evil.example/')
        resp = self.client.get(reverse('notifications:read', args=[n.pk]))
        self.assertRedirects(resp, reverse('notifications:list'))

    def test_cannot_read_someone_elses_notification(self):
        other = User.objects.create_user('eve', 'eve@epi.tn', 'Str0ng-Passw0rd!')
        n = Notification.objects.create(user=other, type='alert', content='x')
        self.assertEqual(self.client.get(reverse('notifications:read', args=[n.pk])).status_code, 404)

    def test_mark_all_read_and_dropdown(self):
        Notification.objects.create(user=self.user, type='alert', content='<b>x</b>')
        data = self.client.get(reverse('notifications:dropdown')).json()
        self.assertEqual(len(data['notifications']), 1)
        self.client.post(reverse('notifications:mark_all_read'))
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())
