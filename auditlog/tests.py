from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user


class SecurityDashboardTests(TestCase):
    def test_superuser_only(self):
        url = reverse('auditlog:dashboard')
        self.assertEqual(self.client.get(url).status_code, 302)  # anonymous -> login
        self.client.force_login(make_user('student'))
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(make_user('admin', is_superuser=True, is_staff=True))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_audit_events_are_logged_as_json_records(self):
        with self.assertLogs('epiconnect.audit', level='INFO') as captured:
            self.client.post(reverse('users:login'), {'username': 'ghost', 'password': 'nope'})
        record = captured.records[0]
        self.assertEqual(record.action, 'login_failed')
        self.assertEqual(record.event, 'audit')
