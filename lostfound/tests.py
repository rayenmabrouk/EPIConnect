import datetime

from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user
from lostfound.models import Item
from wallet.models import Wallet


class LostFoundTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.client.force_login(self.owner)

    def report(self, **extra):
        data = {'title': 'Blue backpack', 'description': 'Left in B12', 'location': 'Block B',
                'date': datetime.date.today().isoformat(), 'item_type': 'lost'}
        data.update(extra)
        return self.client.post(reverse('lostfound:create'), data)

    def test_report_lost_item_awards_points(self):
        self.assertEqual(self.report().status_code, 302)
        item = Item.objects.get()
        self.assertEqual(item.status, 'lost')
        self.assertEqual(item.history.count(), 1)
        self.assertEqual(Wallet.objects.get(user=self.owner).balance, 5)

    def test_status_transitions(self):
        self.report()
        item = Item.objects.get()
        url = reverse('lostfound:status_update', args=[item.pk])
        self.client.post(url, {'status': 'claimed'})  # lost -> claimed is not allowed
        item.refresh_from_db()
        self.assertEqual(item.status, 'lost')
        self.client.post(url, {'status': 'found'})
        item.refresh_from_db()
        self.assertEqual(item.status, 'found')

    def test_stranger_cannot_change_or_delete(self):
        self.report()
        item = Item.objects.get()
        self.client.force_login(make_user('stranger'))
        self.assertEqual(self.client.post(reverse('lostfound:status_update', args=[item.pk]), {'status': 'found'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('lostfound:delete', args=[item.pk])).status_code, 403)

    def test_status_flipping_cannot_farm_points(self):
        # Regression: lost -> found -> lost -> found paid out 10 points every time.
        self.report()
        item = Item.objects.get()
        url = reverse('lostfound:status_update', args=[item.pk])
        for _ in range(3):
            self.client.post(url, {'status': 'found'})
            self.client.post(url, {'status': 'archived'})
            self.client.post(url, {'status': 'lost'})
        self.assertEqual(Wallet.objects.get(user=self.owner).balance, 5 + 10)
