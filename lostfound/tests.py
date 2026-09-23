import datetime

from django.test import TestCase
from django.urls import reverse

from auditlog.models import AuditLog
from lostfound.models import Item
from users.models import StudentProfile, User
from wallet.models import Wallet


class LostFoundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')
        StudentProfile.objects.filter(user=self.user).update(is_verified=True)
        self.client.force_login(self.user)

    def report(self, kind='lost'):
        self.client.post(reverse('lostfound:create'), {
            'item_type': kind, 'title': 'Black wallet', 'description': 'Near the lab',
            'location': 'Bloc B', 'date': datetime.date.today().isoformat(),
        })
        return Item.objects.latest('created_at')

    def balance(self):
        return Wallet.objects.get(user=self.user).balance

    def test_report_item_creates_history_points_and_audit(self):
        item = self.report()
        self.assertEqual(item.status, 'lost')
        self.assertEqual(item.history.count(), 1)
        self.assertEqual(self.balance(), 5)
        self.assertTrue(AuditLog.objects.filter(action='item_create').exists())

    def test_status_flipping_cannot_farm_points(self):
        item = self.report()
        url = reverse('lostfound:status_update', args=[item.pk])
        for status in ('found', 'archived', 'found', 'claimed', 'found', 'claimed'):
            self.client.post(url, {'status': status})
        # 5 (report) + 10 (found, once) + 15 (claimed, once)
        self.assertEqual(self.balance(), 30)

    def test_invalid_transition_rejected(self):
        item = self.report()
        self.client.post(reverse('lostfound:status_update', args=[item.pk]), {'status': 'claimed'})
        item.refresh_from_db()
        self.assertEqual(item.status, 'lost')

    def test_other_user_cannot_change_or_delete(self):
        item = self.report()
        other = User.objects.create_user('eve', 'eve@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('lostfound:status_update', args=[item.pk]), {'status': 'found'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('lostfound:delete', args=[item.pk])).status_code, 403)

    def test_list_and_search(self):
        self.report()
        resp = self.client.get(reverse('lostfound:list'), {'q': 'wallet'})
        self.assertContains(resp, 'Black wallet')
