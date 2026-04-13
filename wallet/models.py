from django.db import models
from django.conf import settings


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s wallet ({self.balance} pts)"


class Transaction(models.Model):
    EARN = 'earn'
    REDEEM = 'redeem'
    TYPE_CHOICES = [(EARN, 'Earned'), (REDEEM, 'Redeemed')]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.type == self.EARN else '-'
        return f"{sign}{self.amount} — {self.description}"


class Perk(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.PositiveIntegerField()
    icon = models.CharField(max_length=10, default='🎁')
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['cost']

    def __str__(self):
        return f"{self.title} ({self.cost} pts)"

    @property
    def available(self):
        if self.stock is None:
            return True
        redeemed = self.redemptions.filter(status__in=['pending', 'claimed']).count()
        return redeemed < self.stock


class Badge(models.Model):
    GOOD_SAMARITAN = 'good_samaritan'
    TRUSTWORTHY_SELLER = 'trustworthy_seller'
    TOP_TUTOR = 'top_tutor'
    ACTIVE_HELPER = 'active_helper'
    FIRST_POST = 'first_post'

    BADGE_CHOICES = [
        (GOOD_SAMARITAN,    'Good Samaritan'),
        (TRUSTWORTHY_SELLER,'Trustworthy Seller'),
        (TOP_TUTOR,         'Top Tutor'),
        (ACTIVE_HELPER,     'Active Helper'),
        (FIRST_POST,        'First Post'),
    ]

    BADGE_META = {
        GOOD_SAMARITAN:     {'icon': '🤝', 'color': 'emerald', 'desc': 'Helped return a lost item to its owner'},
        TRUSTWORTHY_SELLER: {'icon': '⭐', 'color': 'amber',   'desc': 'Created 3 or more marketplace listings'},
        TOP_TUTOR:          {'icon': '🎓', 'color': 'blue',    'desc': 'Received 10 or more likes on Help Wall posts'},
        ACTIVE_HELPER:      {'icon': '💬', 'color': 'purple',  'desc': 'Left 10 or more comments on the Help Wall'},
        FIRST_POST:         {'icon': '🌟', 'color': 'primary', 'desc': 'Published their first Help Wall post'},
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge_type = models.CharField(max_length=30, choices=BADGE_CHOICES)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'badge_type']]
        ordering = ['awarded_at']

    def __str__(self):
        return f"{self.user.username} — {self.get_badge_type_display()}"

    @property
    def meta(self):
        return self.BADGE_META.get(self.badge_type, {})


class Redemption(models.Model):
    PENDING = 'pending'
    CLAIMED = 'claimed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (CLAIMED, 'Claimed')]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='redemptions')
    perk = models.ForeignKey(Perk, on_delete=models.CASCADE, related_name='redemptions')
    points_spent = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-redeemed_at']

    def __str__(self):
        return f"{self.wallet.user.username} redeemed {self.perk.title}"
