from django.db import IntegrityError, transaction
from django.db.models import F

from .models import Wallet, Transaction, Badge


def award_points(user, amount, description, reference=None):
    """Award EPI-points to a user. Creates the wallet if it doesn't exist.

    ``reference`` makes the award idempotent: if a transaction with the same
    reference already exists for this wallet, nothing is awarded again.
    Returns True if points were awarded.
    """
    wallet, _ = Wallet.objects.get_or_create(user=user)
    try:
        with transaction.atomic():
            Transaction.objects.create(
                wallet=wallet,
                type=Transaction.EARN,
                amount=amount,
                description=description[:200],
                reference=reference,
            )
            # F() expression: atomic UPDATE in SQL, safe with concurrent workers
            Wallet.objects.filter(pk=wallet.pk).update(balance=F('balance') + amount)
    except IntegrityError:
        return False  # already awarded for this reference
    return True


def award_badge(user, badge_type):
    """Award a badge to a user if they don't already have it."""
    _, created = Badge.objects.get_or_create(user=user, badge_type=badge_type)
    return created  # True if newly awarded
