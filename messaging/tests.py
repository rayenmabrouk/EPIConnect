import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from messaging.models import Conversation, Message
from notifications.models import Notification
from users.models import User


def png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buf, 'PNG')
    return buf.getvalue()


class MessagingTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user('amine', 'a@epi.tn', 'Str0ng-Passw0rd!')
        self.b = User.objects.create_user('bilel', 'b@epi.tn', 'Str0ng-Passw0rd!')
        self.eve = User.objects.create_user('eve', 'e@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(self.a)
        self.client.get(reverse('messaging:start'), {'user': self.b.pk})
        self.conv = Conversation.objects.get()

    def test_start_conversation_is_reused(self):
        self.client.get(reverse('messaging:start'), {'user': self.b.pk})
        self.assertEqual(Conversation.objects.count(), 1)

    def test_send_and_fetch_message(self):
        resp = self.client.post(reverse('messaging:send', args=[self.conv.pk]), {'content': 'salut'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.b, type='message').exists())
        self.client.force_login(self.b)
        data = self.client.get(reverse('messaging:fetch', args=[self.conv.pk]), {'after': 0}).json()
        self.assertEqual(data['messages'][0]['content'], 'salut')
        self.assertTrue(Message.objects.get().is_read)

    def test_outsider_cannot_read_or_send(self):
        self.client.force_login(self.eve)
        self.assertEqual(self.client.get(reverse('messaging:detail', args=[self.conv.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('messaging:fetch', args=[self.conv.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('messaging:send', args=[self.conv.pk]), {'content': 'x'}).status_code, 403)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='epiconnect-test-media-'))
    def test_image_upload_accepted(self):
        img = SimpleUploadedFile('p.png', png_bytes(), content_type='image/png')
        resp = self.client.post(reverse('messaging:send', args=[self.conv.pk]), {'image': img})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()['image_url'])

    def test_non_image_upload_rejected(self):
        evil = SimpleUploadedFile('x.html', b'<script>alert(1)</script>', content_type='image/png')
        resp = self.client.post(reverse('messaging:send', args=[self.conv.pk]), {'image': evil})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Message.objects.exists())
