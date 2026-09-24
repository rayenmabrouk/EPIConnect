from django.test import TestCase
from django.urls import reverse

from auditlog.models import AuditLog
from core.testutils import PASSWORD, make_user
from users.models import StudentProfile, User


class RegistrationTests(TestCase):
    def _register(self, **overrides):
        data = {
            'username': 'newstudent', 'email': 'new@epi.test', 'first_name': 'New',
            'last_name': 'Student', 'student_id': 'EPI2026001',
            'password1': PASSWORD, 'password2': PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse('users:register'), data)

    def test_register_stores_student_id_and_audits(self):
        # Regression: this code path contained unresolved merge-conflict markers.
        response = self._register()
        self.assertRedirects(response, reverse('users:login'))
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.profile.student_id, 'EPI2026001')
        self.assertFalse(user.profile.is_verified)
        self.assertTrue(AuditLog.objects.filter(action='register', user=user).exists())

    def test_duplicate_student_id_rejected(self):
        make_user('existing')
        response = self._register(student_id='EPI-existing')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already registered')

    def test_weak_password_rejected(self):
        response = self._register(password1='12345678', password2='12345678')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newstudent').exists())


class LoginTests(TestCase):
    def test_login_and_audit(self):
        user = make_user('bob')
        response = self.client.post(reverse('users:login'), {'username': 'bob', 'password': PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action='login', user=user).exists())

    def test_bruteforce_lockout_after_five_failures(self):
        make_user('carol')
        for _ in range(5):
            self.client.post(reverse('users:login'), {'username': 'carol', 'password': 'wrong'})
        # Even the right password is refused while locked out.
        response = self.client.post(reverse('users:login'), {'username': 'carol', 'password': PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.assertTrue(AuditLog.objects.filter(action='account_locked').exists())
        # The attempt made while locked out is recorded as well.
        self.assertGreaterEqual(AuditLog.objects.filter(action='login_failed').count(), 5)


class VerificationTests(TestCase):
    def test_unverified_student_cannot_post(self):
        user = make_user('dave', verified=False)
        self.client.force_login(user)
        for name in ['social:create', 'lostfound:create', 'marketplace:create']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_verified_student_cannot_change_student_id(self):
        user = make_user('erin', verified=True)
        self.client.force_login(user)
        self.client.post(reverse('users:profile_edit'), {
            'first_name': 'E', 'last_name': 'R', 'email': 'erin@epi.test',
            'student_id': 'SOMEONE-ELSE', 'bio': 'hi',
        })
        self.assertEqual(StudentProfile.objects.get(user=user).student_id, 'EPI-erin')

    def test_profile_picture_must_be_an_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        user = make_user('fred', verified=False)
        self.client.force_login(user)
        fake = SimpleUploadedFile('evil.html', b'<script>alert(1)</script>', content_type='text/html')
        response = self.client.post(reverse('users:profile_edit'), {
            'first_name': 'F', 'last_name': 'R', 'email': 'fred@epi.test',
            'student_id': 'EPI-fred', 'bio': '', 'profile_picture': fake,
        })
        self.assertEqual(response.status_code, 200)  # form re-rendered with an error
        self.assertFalse(StudentProfile.objects.get(user=user).profile_picture)
