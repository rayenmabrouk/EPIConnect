from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from auditlog.models import AuditLog
from users.models import StudentProfile, User
from wallet.models import Wallet


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters

    def _payload(self, n=1):
        return {
            'username': f'student{n}',
            'email': f'student{n}@epi.tn',
            'first_name': 'Test',
            'last_name': 'Student',
            'student_id': f'EPI2026{n:03d}',
            'password1': 'Str0ng-Passw0rd!',
            'password2': 'Str0ng-Passw0rd!',
        }

    def test_register_creates_user_profile_and_audit_log(self):
        resp = self.client.post(reverse('users:register'), self._payload())
        self.assertRedirects(resp, reverse('users:login'))
        user = User.objects.get(username='student1')
        self.assertEqual(user.profile.student_id, 'EPI2026001')
        self.assertFalse(user.profile.is_verified)
        self.assertTrue(AuditLog.objects.filter(action='register', user=user).exists())

    def test_duplicate_student_id_rejected(self):
        self.client.post(reverse('users:register'), self._payload(1))
        dup = self._payload(2)
        dup['student_id'] = 'EPI2026001'
        resp = self.client.post(reverse('users:register'), dup)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'already registered')
        self.assertFalse(User.objects.filter(username='student2').exists())

    def test_short_password_rejected(self):
        data = self._payload()
        data['password1'] = data['password2'] = 'abc12'
        self.client.post(reverse('users:register'), data)
        self.assertFalse(User.objects.filter(username='student1').exists())

    def test_register_is_rate_limited_per_ip(self):
        for i in range(5):
            self.client.post(reverse('users:register'), self._payload(i + 10), REMOTE_ADDR='41.0.0.1')
        resp = self.client.post(reverse('users:register'), self._payload(99), REMOTE_ADDR='41.0.0.1')
        self.assertEqual(resp.status_code, 403)
        # a different client IP is not affected
        resp = self.client.post(reverse('users:register'), self._payload(98), REMOTE_ADDR='41.0.0.2')
        self.assertEqual(resp.status_code, 302)


class VerificationGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(self.user)

    def test_unverified_student_cannot_create_content(self):
        for url in ('lostfound:create', 'marketplace:create', 'social:create'):
            resp = self.client.get(reverse(url))
            self.assertEqual(resp.status_code, 403, url)

    def test_verified_student_can_create_content(self):
        StudentProfile.objects.filter(user=self.user).update(is_verified=True)
        for url in ('lostfound:create', 'marketplace:create', 'social:create'):
            self.assertEqual(self.client.get(reverse(url)).status_code, 200, url)


class ProfileTests(TestCase):
    def test_profile_signal_and_wallet_created_lazily(self):
        user = User.objects.create_user('sara', 'sara@epi.tn', 'Str0ng-Passw0rd!')
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.client.force_login(user)
        self.client.get(reverse('core:home'))
        self.assertTrue(Wallet.objects.filter(user=user).exists())

    def test_public_profile_page(self):
        user = User.objects.create_user('sara', 'sara@epi.tn', 'Str0ng-Passw0rd!')
        self.assertEqual(self.client.get(reverse('users:profile', args=[user.pk])).status_code, 200)
