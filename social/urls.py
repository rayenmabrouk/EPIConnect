from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('', views.FeedView.as_view(), name='feed'),
    path('create/', views.PostCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PostDetailView.as_view(), name='detail'),
    path('<int:pk>/comment/', views.CommentCreateView.as_view(), name='comment'),
    path('<int:pk>/like/', views.LikeToggleView.as_view(), name='like'),
    path('<int:pk>/delete/', views.PostDeleteView.as_view(), name='delete'),
    path('comment/<int:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
]
