"""
EPIConnect settings.

All environment-specific values come from environment variables, loaded from
a ``.env`` file at the project root (see ``.env.example``).
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool('DEBUG', False)

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY and DEBUG:
    # Local development only: random per-process key (sessions reset on restart)
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'SECRET_KEY is not set. Add it to .env (see .env.example) or set DEBUG=True for local development.'
    )

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django_prometheus',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'core',
    'lostfound',
    'marketplace',
    'social',
    'messaging',
    'notifications',
    'wallet',
    'axes',
    'auditlog',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # AxesMiddleware should be the last middleware in the list
    'axes.middleware.AxesMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'epiconnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications_count',
                'messaging.context_processors.unread_messages_count',
                'wallet.context_processors.wallet_balance',
            ],
        },
    },
]

WSGI_APPLICATION = 'epiconnect.wsgi.application'

# ---------------------------------------------------------------------------
# Database — PostgreSQL in production (DATABASE_URL), SQLite locally.
# The django_prometheus backends are drop-in wrappers that export
# django_db_* metrics for the Grafana "Django" dashboard (#17658).
# ---------------------------------------------------------------------------
_DATABASE_URL = os.environ.get('DATABASE_URL')
if _DATABASE_URL:
    import dj_database_url
    _engine = None
    if _DATABASE_URL.startswith(('postgres://', 'postgresql://')):
        _engine = 'django_prometheus.db.backends.postgresql'
    DATABASES = {'default': dj_database_url.parse(_DATABASE_URL, conn_max_age=600, engine=_engine)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django_prometheus.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Per-process cache. django-ratelimit counters are therefore per Gunicorn
# worker (effective limit = rate x workers) — acceptable for a demo; switch to
# Redis/Memcached for strict limits.
CACHES = {
    'default': {
        'BACKEND': 'django_prometheus.cache.backends.locmem.LocMemCache',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('TIME_ZONE', 'Africa/Tunis')
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [p for p in [BASE_DIR / 'static'] if p.exists()]
STORAGES = {
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# Nginx terminates TLS and sets X-Forwarded-Proto. Trusting it makes
# request.is_secure() correct behind the proxy, which is what the CSRF origin
# check needs (this was the root cause of the "CSRF 500 behind Nginx" issue;
# no need to disable CSRF_COOKIE_SECURE any more).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS=True once Let's Encrypt is in place; set HTTPS=False when serving the
# demo over plain http://<ip> (otherwise browsers drop the secure cookies).
HTTPS = env_bool('HTTPS', not DEBUG)
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SESSION_COOKIE_HTTPONLY = True
if HTTPS:
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = False  # Nginx handles the HTTP -> HTTPS redirect
SILENCED_SYSTEM_CHECKS = [
    'security.W008',  # SSL redirect is done by Nginx, not Django
    'security.W021',  # HSTS preload list is not applicable to *.cloudapp.azure.com
]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Real client IP (behind Nginx) for axes, ratelimit and the audit log
AXES_CLIENT_IP_CALLABLE = 'core.utils.get_client_ip'
RATELIMIT_IP_META_KEY = 'core.utils.get_client_ip'

# django-axes — brute-force protection
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ADMIN = True
AXES_LOCKOUT_TEMPLATE = 'security/lockout.html'

# Uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Logging — everything to stdout/stderr, collected by journald
# (journalctl -u gunicorn)
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'), 'propagate': False},
        'axes': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
