from django.test import TestCase
from django.urls import reverse

from auditlog.models import AuditLog
from users.models import User


class SecurityDashboardTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse('auditlog:dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('users:login'), resp['Location'])

    def test_regular_user_forbidden(self):
        user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('auditlog:dashboard')).status_code, 403)

    def test_superuser_sees_dashboard(self):
        admin = User.objects.create_superuser('root', 'root@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('auditlog:dashboard')).status_code, 200)


class LoginAuditAndLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')

    def login(self, password, ip='41.0.0.1'):
        return self.client.post(reverse('users:login'), {'username': 'ali', 'password': password},
                                REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP=ip)

    def test_successful_login_is_logged_with_real_ip(self):
        self.login('Str0ng-Passw0rd!')
        log = AuditLog.objects.get(action='login')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.ip_address, '41.0.0.1')

    def test_failed_logins_logged_and_account_locked_after_five(self):
        for _ in range(5):
            self.login('wrong')
        self.assertEqual(AuditLog.objects.filter(action='login_failed').count(), 5)
        self.assertTrue(AuditLog.objects.filter(action='account_locked').exists())
        resp = self.login('Str0ng-Passw0rd!')
        self.assertEqual(resp.status_code, 429)
