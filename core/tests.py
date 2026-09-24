from django.test import TestCase, override_settings
from django.urls import reverse

from core.testutils import make_user


class HealthCheckTests(TestCase):
    def test_healthz_bypasses_allowed_hosts(self):
        # The ALB health checker uses the task's private IP as Host header.
        response = self.client.get('/healthz/', HTTP_HOST='10.0.1.23')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_readyz_checks_database(self):
        response = self.client.get('/readyz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['database'], 'ok')

    def test_unknown_host_still_rejected_for_normal_pages(self):
        response = self.client.get('/', HTTP_HOST='evil.example.com')
        self.assertEqual(response.status_code, 400)


class TrustedProxyTests(TestCase):
    def _ip_seen_by_audit_log(self, **headers):
        from auditlog.models import AuditLog
        self.client.post(reverse('users:login'), {'username': 'nobody', 'password': 'x'}, **headers)
        return AuditLog.objects.filter(action='login_failed').latest('timestamp').ip_address

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_spoofed_left_most_entry_is_ignored(self):
        # Client sends a fake XFF; the ALB appends the address it really saw.
        ip = self._ip_seen_by_audit_log(
            HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7', REMOTE_ADDR='10.0.1.5'
        )
        self.assertEqual(ip, '203.0.113.7')

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_two_proxies(self):
        # e.g. CloudFront -> ALB: client is second from the right
        ip = self._ip_seen_by_audit_log(
            HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7, 130.176.0.10', REMOTE_ADDR='10.0.1.5'
        )
        self.assertEqual(ip, '203.0.113.7')

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_header_ignored_without_trusted_proxies(self):
        ip = self._ip_seen_by_audit_log(HTTP_X_FORWARDED_FOR='6.6.6.6', REMOTE_ADDR='198.51.100.1')
        self.assertEqual(ip, '198.51.100.1')


class SecurityHeaderTests(TestCase):
    def test_csp_with_nonce_and_no_third_party_script(self):
        response = self.client.get('/')
        csp = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self' 'nonce-", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn('cdn.tailwindcss.com', response.content.decode())
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertIn(f'nonce="{nonce}"', response.content.decode())

    def test_no_inline_event_handlers_in_rendered_pages(self):
        user = make_user('alice')
        self.client.force_login(user)
        for url in ['/', '/social/', '/lostfound/', '/marketplace/', '/wallet/perks/', '/users/profile/edit/']:
            html = self.client.get(url).content.decode()
            for attr in (' onclick=', ' onsubmit=', ' onchange='):
                self.assertNotIn(attr, html, f'{attr} found on {url}')

    def test_standard_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')


class PublicPagesTests(TestCase):
    def test_public_pages_render(self):
        for name in ['core:home', 'social:feed', 'lostfound:list', 'marketplace:list',
                     'wallet:leaderboard', 'users:login', 'users:register']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_private_pages_require_login(self):
        for name in ['users:dashboard', 'messaging:inbox', 'notifications:list', 'wallet:wallet']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn('/users/login/', response['Location'])
