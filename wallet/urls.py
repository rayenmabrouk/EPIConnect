from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('', views.WalletView.as_view(), name='wallet'),
    path('perks/', views.PerksView.as_view(), name='perks'),
    path('perks/<int:pk>/redeem/', views.RedeemView.as_view(), name='redeem'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]
