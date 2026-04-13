from django.urls import path
from . import views

app_name = 'lostfound'

urlpatterns = [
    path('', views.ItemListView.as_view(), name='list'),
    path('create/', views.ItemCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ItemDetailView.as_view(), name='detail'),
    path('<int:pk>/status/', views.ItemStatusUpdateView.as_view(), name='status_update'),
    path('<int:pk>/delete/', views.ItemDeleteView.as_view(), name='delete'),
]
