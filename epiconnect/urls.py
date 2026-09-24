from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from core.views import favicon

urlpatterns = [
    path('favicon.ico', favicon),
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('lostfound/', include('lostfound.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('social/', include('social.urls')),
    path('messaging/', include('messaging.urls')),
    path('notifications/', include('notifications.urls')),
    path('wallet/', include('wallet.urls')),
    path('security/', include('auditlog.urls')),
]

# Local development / docker compose only. On AWS, media lives in S3 and is
# served to browsers through pre-signed URLs; Django never serves user uploads in production.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
