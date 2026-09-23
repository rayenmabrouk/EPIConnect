from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from marketplace.models import Listing
from users.models import StudentProfile, User


class MarketplaceTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', 's@epi.tn', 'Str0ng-Passw0rd!')
        StudentProfile.objects.filter(user=self.seller).update(is_verified=True)
        self.client.force_login(self.seller)

    def create(self, n):
        return self.client.post(reverse('marketplace:create'), {
            'title': f'Book {n}', 'description': 'Good state', 'price': '12.50', 'category': 'books',
        })

    def test_create_listing_and_trustworthy_badge_after_three(self):
        for n in range(3):
            self.create(n)
        self.assertEqual(Listing.objects.filter(seller=self.seller).count(), 3)
        self.assertEqual(Listing.objects.first().price, Decimal('12.50'))
        self.assertTrue(self.seller.badges.filter(badge_type='trustworthy_seller').exists())

    def test_filter_and_sort(self):
        Listing.objects.create(seller=self.seller, title='Cheap', description='x', price=1, category='books')
        Listing.objects.create(seller=self.seller, title='Pricey', description='x', price=99, category='electronics')
        resp = self.client.get(reverse('marketplace:list'), {'sort': 'price_desc'})
        titles = [l.title for l in resp.context['listings']]
        self.assertEqual(titles, ['Pricey', 'Cheap'])
        resp = self.client.get(reverse('marketplace:list'), {'category': 'books'})
        self.assertEqual([l.title for l in resp.context['listings']], ['Cheap'])

    def test_only_seller_can_delete(self):
        listing = Listing.objects.create(seller=self.seller, title='X', description='x', price=1)
        other = User.objects.create_user('eve', 'eve@epi.tn', 'Str0ng-Passw0rd!')
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('marketplace:delete', args=[listing.pk])).status_code, 403)
