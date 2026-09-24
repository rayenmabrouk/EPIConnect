from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user
from wallet.models import Perk, Redemption, Wallet
from wallet.utils import award_points


class RedeemTests(TestCase):
    def setUp(self):
        self.user = make_user('saver')
        self.client.force_login(self.user)
        self.perk = Perk.objects.create(title='Coffee', description='One coffee', cost=50, stock=1)

    def test_redeem_debits_balance(self):
        award_points(self.user, 60, 'test')
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 10)
        self.assertEqual(Redemption.objects.count(), 1)

    def test_insufficient_balance(self):
        award_points(self.user, 10, 'test')
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 10)
        self.assertEqual(Redemption.objects.count(), 0)

    def test_stock_is_enforced(self):
        award_points(self.user, 200, 'test')
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Redemption.objects.count(), 1)
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 150)

    def test_redeem_requires_post(self):
        self.assertEqual(self.client.get(reverse('wallet:redeem', args=[self.perk.pk])).status_code, 405)


class AwardPointsTests(TestCase):
    def test_award_is_additive(self):
        user = make_user('earner')
        award_points(user, 5, 'a')
        award_points(user, 7, 'b')
        wallet = Wallet.objects.get(user=user)
        self.assertEqual(wallet.balance, 12)
        self.assertEqual(wallet.transactions.count(), 2)
