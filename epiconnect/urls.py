from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import healthz, metrics

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('lostfound/', include('lostfound.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('social/', include('social.urls')),
    path('messaging/', include('messaging.urls')),
    path('notifications/', include('notifications.urls')),
    path('wallet/', include('wallet.urls')),
    path('security/', include('auditlog.urls')),
    # Ops endpoints
    path('healthz/', healthz, name='healthz'),
    path('metrics', metrics, name='prometheus-django-metrics'),
]

# Only active when DEBUG=True; in production Nginx serves /media/ directly.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
