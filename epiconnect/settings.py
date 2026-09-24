"""EPIConnect settings.

All deployment-specific values come from environment variables so the same
container image runs locally (docker compose) and on AWS (ECS Fargate).
See .env.example for the full list.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # optional: local development convenience only
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:  # pragma: no cover
    pass


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool('DEBUG', False)

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is off.')
    # Only reachable with DEBUG on (local development)
    SECRET_KEY = 'django-insecure-local-development-only'  # nosec B105

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
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
    'core.middleware.HealthCheckMiddleware',
    'core.middleware.TrustedProxyMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
]

ROOT_URLCONF = 'epiconnect.urls'
WSGI_APPLICATION = 'epiconnect.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.csp',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications_count',
                'messaging.context_processors.unread_messages_count',
                'wallet.context_processors.wallet_balance',
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database
# DATABASE_URL (local / compose) or discrete DB_* variables (ECS injects the
# password as its own secret, so it never appears inside a URL string).
# --------------------------------------------------------------------------
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=60)}
elif os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': os.environ['DB_HOST'],
            'PORT': os.environ.get('DB_PORT', '5432'),
            'NAME': os.environ.get('DB_NAME', 'epiconnect'),
            'USER': os.environ.get('DB_USER', 'epiconnect'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require')},
        }
    }
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'users.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files (WhiteNoise, baked into the image) and media (S3 on AWS)
# --------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

_static_backend = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if env_bool('STATIC_MANIFEST', True)
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)
STORAGES = {
    'staticfiles': {'BACKEND': _static_backend},
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
SERVE_MEDIA = env_bool('SERVE_MEDIA', DEBUG)  # local only; on AWS uploads are served from S3

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
MEDIA_HOSTS = []
if AWS_STORAGE_BUCKET_NAME:
    # Uploads live in a private S3 bucket. Browsers get short-lived pre-signed
    # URLs (SigV4, 1 hour) generated per page render: nothing in the bucket is
    # ever public, and user content is served from a different origin than the
    # application (a malicious file could not run script on our domain).
    _region = os.environ.get('AWS_REGION', 'us-east-1')
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': AWS_STORAGE_BUCKET_NAME,
            'region_name': _region,
            'location': 'media',
            'signature_version': 's3v4',
            'addressing_style': 'virtual',
            'querystring_auth': True,
            'querystring_expire': 3600,
            'file_overwrite': False,
            'default_acl': None,
            'object_parameters': {'CacheControl': 'private, max-age=3600'},
        },
    }
    MEDIA_HOSTS = [
        f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com',
        f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{_region}.amazonaws.com',
    ]

MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE_MB', '5')) * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE + 1024 * 1024

# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------
# Number of reverse proxies in front of the app that append to X-Forwarded-For
# (the ALB on AWS = 1, none locally = 0). See core/middleware.py.
TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT', '0'))

# Header set by the load balancer with the scheme the browser used
# (HTTP_X_FORWARDED_PROTO behind an ALB). Trustworthy only because the task
# accepts traffic from the ALB security group alone, and the ALB overwrites it.
_proxy_ssl_header = os.environ.get('SECURE_PROXY_SSL_HEADER', '')
if _proxy_ssl_header:
    SECURE_PROXY_SSL_HEADER = (_proxy_ssl_header, 'https')

SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('SECURE_COOKIES', not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # we do not own the parent domain (cloudfront.net)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Nonce-based Content Security Policy (Django 6 built-in). No third-party
# script is loaded at runtime: Tailwind is compiled at image build time.
SECURE_CSP = {
    'default-src': [CSP.SELF],
    'script-src': [CSP.SELF, CSP.NONCE],
    'style-src': [CSP.SELF, CSP.UNSAFE_INLINE],  # templates use style="" attributes
    'img-src': [CSP.SELF, 'data:', 'blob:'],
    'font-src': [CSP.SELF],
    'connect-src': [CSP.SELF],
    'object-src': [CSP.NONE],
    'base-uri': [CSP.SELF],
    'form-action': [CSP.SELF],
    'frame-ancestors': [CSP.NONE],
}
SECURE_CSP['img-src'] += MEDIA_HOSTS  # pre-signed S3 URLs for uploads

ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# django-axes: brute-force protection (lock username+IP after 5 failures for 1h)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ADMIN = True
AXES_LOCKOUT_TEMPLATE = 'security/lockout.html'
AXES_IPWARE_META_PRECEDENCE_ORDER = ('REMOTE_ADDR',)  # already resolved by TrustedProxyMiddleware

# Rate-limit counters must be shared by every Gunicorn worker and every ECS
# task, so they live in PostgreSQL (DatabaseCache) rather than per-process
# memory. DB increments are not atomic: under a burst a few extra requests can
# slip through, which is acceptable here and avoids paying for ElastiCache.
# A production deployment with real traffic would use Redis/Valkey.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
    }
}
SILENCED_SYSTEM_CHECKS = [
    'django_ratelimit.E003', 'django_ratelimit.W001',
    # HSTS includeSubDomains/preload are deliberately off: the app is served on a
    # cloudfront.net subdomain and we do not control the parent domain.
    'security.W005', 'security.W021',
]
RATELIMIT_VIEW = 'core.views.ratelimited'  # HTTP 429 instead of a generic 403

# --------------------------------------------------------------------------
# Logging: JSON lines on stdout -> CloudWatch Logs (awslogs driver)
# --------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {'()': 'core.logging.JsonFormatter'},
        'plain': {'format': '%(levelname)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if env_bool('LOG_JSON', not DEBUG) else 'plain',
        },
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'axes': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'epiconnect.audit': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
