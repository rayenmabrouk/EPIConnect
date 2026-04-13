from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.InboxView.as_view(), name='inbox'),
    path('start/', views.StartConversationView.as_view(), name='start'),
    path('<int:pk>/', views.ConversationDetailView.as_view(), name='detail'),
    path('<int:pk>/send/', views.SendMessageView.as_view(), name='send'),
    path('<int:pk>/fetch/', views.FetchMessagesView.as_view(), name='fetch'),
]
