from django.urls import path
from . import views

app_name = 'auditlog'

urlpatterns = [
    path('dashboard/', views.security_dashboard, name='dashboard'),
]
