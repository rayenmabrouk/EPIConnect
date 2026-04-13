from .models import Wallet, Transaction, Badge


def award_points(user, amount, description):
    """Award EPI-points to a user. Creates wallet if it doesn't exist."""
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.balance += amount
    wallet.save(update_fields=['balance'])
    Transaction.objects.create(
        wallet=wallet,
        type=Transaction.EARN,
        amount=amount,
        description=description,
    )


def award_badge(user, badge_type):
    """Award a badge to a user if they don't already have it."""
    _, created = Badge.objects.get_or_create(user=user, badge_type=badge_type)
    return created  # True if newly awarded
