from django.core.management.base import BaseCommand
from wallet.models import Perk

PERKS = [
    {'title': 'Free Coffee', 'description': 'One free coffee at the campus cafeteria.', 'cost': 50, 'icon': '☕'},
    {'title': 'Extra Printing', 'description': '20 extra black & white printing pages at the library.', 'cost': 30, 'icon': '🖨️'},
    {'title': 'Book Loan Extension', 'description': 'Extend a library book loan by 7 days without a fine.', 'cost': 25, 'icon': '📚'},
    {'title': 'Campus Store 10% Discount', 'description': '10% off your next purchase at the campus store.', 'cost': 80, 'icon': '🛍️'},
    {'title': 'Locker Rental (1 week)', 'description': 'One week free locker rental on campus.', 'cost': 60, 'icon': '🔒'},
    {'title': 'Priority Seat Reservation', 'description': 'Reserve a study room for 2 hours at the library.', 'cost': 40, 'icon': '🪑'},
    {'title': 'Free Snack', 'description': 'One free snack from the campus vending machines.', 'cost': 35, 'icon': '🍫'},
    {'title': 'EPI Hoodie Discount', 'description': '15% off official EPI merchandise.', 'cost': 150, 'icon': '👕'},
]


class Command(BaseCommand):
    help = 'Seed default campus perks'

    def handle(self, *args, **options):
        created = 0
        for data in PERKS:
            _, was_created = Perk.objects.get_or_create(title=data['title'], defaults=data)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} perks ({len(PERKS) - created} already existed).'))
