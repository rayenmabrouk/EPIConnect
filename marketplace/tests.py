from django.test import TestCase
from django.urls import reverse

from core.testutils import make_user
from marketplace.models import Listing


class ListingTests(TestCase):
    def setUp(self):
        self.seller = make_user('seller')
        self.client.force_login(self.seller)

    def test_create_listing(self):
        response = self.client.post(reverse('marketplace:create'), {
            'title': 'Networking book', 'description': 'CCNA guide', 'price': '25.00', 'category': 'books',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Listing.objects.get().seller, self.seller)

    def test_negative_price_rejected(self):
        response = self.client.post(reverse('marketplace:create'), {
            'title': 'Free money', 'description': 'x', 'price': '-10', 'category': 'other',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 0)

    def test_only_seller_can_delete(self):
        listing = Listing.objects.create(title='t', description='d', price=1, seller=self.seller)
        self.client.force_login(make_user('thief'))
        self.assertEqual(self.client.post(reverse('marketplace:delete', args=[listing.pk])).status_code, 403)

    def test_search_and_filter(self):
        Listing.objects.create(title='Laptop', description='d', price=300, category='electronics', seller=self.seller)
        Listing.objects.create(title='Chair', description='d', price=20, category='furniture', seller=self.seller)
        response = self.client.get(reverse('marketplace:list'), {'category': 'electronics'})
        self.assertContains(response, 'Laptop')
        self.assertNotContains(response, 'Chair')
