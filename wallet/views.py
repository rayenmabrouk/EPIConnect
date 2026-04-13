from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from .models import Wallet, Transaction, Perk, Redemption, Badge


class WalletView(LoginRequiredMixin, View):
    EARN_ACTIONS = [
        ('post', 1, 'Publish a Help Wall post'),
        ('comment', 2, 'Leave a comment'),
        ('commented', 3, 'Your post gets commented on'),
        ('liked', 2, 'Your post gets liked'),
        ('report', 5, 'Report a lost/found item'),
        ('found', 10, 'Mark an item as found'),
        ('claimed', 15, 'Item gets claimed'),
    ]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        transactions = wallet.transactions.all()[:30]
        redemptions = wallet.redemptions.select_related('perk').all()[:10]
        return render(request, 'wallet/wallet.html', {
            'wallet': wallet,
            'transactions': transactions,
            'redemptions': redemptions,
            'earn_actions': self.EARN_ACTIONS,
        })


class PerksView(LoginRequiredMixin, View):
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        perks = Perk.objects.filter(is_active=True)
        return render(request, 'wallet/perks.html', {
            'wallet': wallet,
            'perks': perks,
        })


class LeaderboardView(View):
    def get(self, request):
        from django.db.models import Q
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        top_wallets = (
            Wallet.objects
            .annotate(monthly_pts=Sum(
                'transactions__amount',
                filter=Q(transactions__type=Transaction.EARN,
                         transactions__created_at__gte=month_start),
            ))
            .filter(monthly_pts__isnull=False)
            .order_by('-monthly_pts')
            .select_related('user', 'user__profile')[:10]
        )

        leaderboard = []
        for i, wallet in enumerate(top_wallets, start=1):
            badges = Badge.objects.filter(user=wallet.user)
            leaderboard.append({
                'rank': i,
                'wallet': wallet,
                'badges': badges,
                'monthly_pts': wallet.monthly_pts or 0,
            })

        user_badges = Badge.objects.filter(user=request.user) if request.user.is_authenticated else []

        # Pre-combine choices + meta so templates need no custom filters
        badge_types = [
            {'code': code, 'label': label, **Badge.BADGE_META[code]}
            for code, label in Badge.BADGE_CHOICES
        ]

        return render(request, 'wallet/leaderboard.html', {
            'leaderboard': leaderboard,
            'month': now.strftime('%B %Y'),
            'user_badges': user_badges,
            'badge_types': badge_types,
        })


class RedeemView(LoginRequiredMixin, View):
    def post(self, request, pk):
        perk = get_object_or_404(Perk, pk=pk, is_active=True)
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        if not perk.available:
            messages.error(request, f'"{perk.title}" is out of stock.')
            return redirect(reverse('wallet:perks'))

        if wallet.balance < perk.cost:
            messages.error(request, f'Not enough points. You need {perk.cost} pts but have {wallet.balance} pts.')
            return redirect(reverse('wallet:perks'))

        wallet.balance -= perk.cost
        wallet.save(update_fields=['balance'])

        Transaction.objects.create(
            wallet=wallet,
            type=Transaction.REDEEM,
            amount=perk.cost,
            description=f'Redeemed: {perk.title}',
        )
        Redemption.objects.create(
            wallet=wallet,
            perk=perk,
            points_spent=perk.cost,
        )

        messages.success(request, f'You redeemed "{perk.title}"! Show this page at the campus desk to claim it.')
        return redirect(reverse('wallet:wallet'))
