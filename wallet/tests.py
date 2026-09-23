from django.test import TestCase
from django.urls import reverse

from users.models import User
from wallet.models import Perk, Redemption, Transaction, Wallet
from wallet.utils import award_badge, award_points


class AwardPointsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')

    def test_award_points_updates_balance_and_ledger(self):
        award_points(self.user, 5, 'test')
        award_points(self.user, 3, 'test')
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 8)
        self.assertEqual(wallet.transactions.count(), 2)

    def test_reference_makes_award_idempotent(self):
        self.assertTrue(award_points(self.user, 2, 'like', reference='like:1:2'))
        self.assertFalse(award_points(self.user, 2, 'like', reference='like:1:2'))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 2)

    def test_badge_awarded_once(self):
        self.assertTrue(award_badge(self.user, 'first_post'))
        self.assertFalse(award_badge(self.user, 'first_post'))


class RedeemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ali', 'ali@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(self.user)
        self.perk = Perk.objects.create(title='Coffee', description='x', cost=50, stock=1)

    def test_cannot_redeem_without_enough_points(self):
        award_points(self.user, 10, 'seed')
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 10)
        self.assertFalse(Redemption.objects.exists())

    def test_redeem_deducts_points_and_respects_stock(self):
        award_points(self.user, 120, 'seed')
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 70)
        self.assertEqual(Transaction.objects.filter(type='redeem').count(), 1)
        # stock = 1 -> second redemption refused
        self.client.post(reverse('wallet:redeem', args=[self.perk.pk]))
        self.assertEqual(Wallet.objects.get(user=self.user).balance, 70)
        self.assertEqual(Redemption.objects.count(), 1)

    def test_pages_render(self):
        for name in ('wallet:wallet', 'wallet:perks', 'wallet:leaderboard'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
