import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.testutils import make_user, png_upload
from messaging.models import Conversation, Message

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class MessagingTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.alice = make_user('alice')
        self.bob = make_user('bob')
        self.mallory = make_user('mallory')
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.alice, self.bob)

    def send(self, user, **data):
        self.client.force_login(user)
        return self.client.post(reverse('messaging:send', args=[self.conv.pk]), data)

    def test_participant_can_send_and_other_is_notified(self):
        response = self.send(self.alice, content='hello')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.get().content, 'hello')
        self.assertEqual(self.bob.notifications.count(), 1)

    def test_non_participant_forbidden(self):
        self.assertEqual(self.send(self.mallory, content='hi').status_code, 403)
        self.client.force_login(self.mallory)
        self.assertEqual(self.client.get(reverse('messaging:detail', args=[self.conv.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('messaging:fetch', args=[self.conv.pk])).status_code, 403)

    def test_empty_message_rejected(self):
        self.assertEqual(self.send(self.alice, content='   ').status_code, 400)

    def test_image_upload_is_renamed(self):
        response = self.send(self.alice, image=png_upload('my holiday.png'))
        self.assertEqual(response.status_code, 200)
        name = Message.objects.get().image.name
        self.assertTrue(name.startswith('message_images/'))
        self.assertNotIn('holiday', name)
        self.assertTrue(name.endswith('.png'))

    def test_non_image_upload_rejected(self):
        # Regression: this endpoint used to store any file, e.g. an HTML page (stored XSS).
        evil = SimpleUploadedFile('evil.html', b'<script>alert(1)</script>', content_type='text/html')
        self.assertEqual(self.send(self.alice, image=evil).status_code, 400)
        disguised = SimpleUploadedFile('evil.png', b'<script>alert(1)</script>', content_type='image/png')
        self.assertEqual(self.send(self.alice, image=disguised).status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    @override_settings(MAX_UPLOAD_SIZE=100)
    def test_oversized_image_rejected(self):
        self.assertEqual(self.send(self.alice, image=png_upload(size=(64, 64))).status_code, 400)
