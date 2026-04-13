from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.ListingListView.as_view(), name='list'),
    path('create/', views.ListingCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ListingDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.ListingDeleteView.as_view(), name='delete'),
]
