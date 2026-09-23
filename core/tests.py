from django.test import RequestFactory, TestCase

from core.utils import get_client_ip


class ClientIpTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_uses_x_real_ip_set_by_nginx(self):
        req = self.rf.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='41.226.1.2')
        self.assertEqual(get_client_ip(req), '41.226.1.2')

    def test_ignores_spoofable_x_forwarded_for(self):
        req = self.rf.get('/', REMOTE_ADDR='10.0.0.5', HTTP_X_FORWARDED_FOR='1.2.3.4')
        self.assertEqual(get_client_ip(req), '10.0.0.5')

    def test_none_request(self):
        self.assertIsNone(get_client_ip(None))


class OpsEndpointTests(TestCase):
    def test_home_page_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_healthz_ok(self):
        resp = self.client.get('/healthz/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'ok'})

    def test_metrics_allowed_from_loopback(self):
        resp = self.client.get('/metrics', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'django_http_requests', resp.content)

    def test_metrics_forbidden_through_nginx(self):
        resp = self.client.get('/metrics', REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='41.226.1.2')
        self.assertEqual(resp.status_code, 403)

    def test_metrics_forbidden_from_remote(self):
        resp = self.client.get('/metrics', REMOTE_ADDR='41.226.1.2')
        self.assertEqual(resp.status_code, 403)
