from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
]

# Serve user-uploaded media files.
# Django/gunicorn handles this directly on Azure App Service, which is fine
# for a low-traffic deployment. For high traffic, switch to Azure Blob Storage.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
