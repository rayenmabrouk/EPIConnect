import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file when running locally
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-local-dev-only-do-not-use-in-production',
)

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

# Required for POST requests to work behind Azure's HTTPS proxy
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Project apps
    'users',
    'core',
    'lostfound',
    'marketplace',
    'social',
    'messaging',
    'notifications',
    'wallet',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

# ── Database ──────────────────────────────────────────────────────────────────
# Set DATABASE_URL env var to use PostgreSQL (recommended for Azure).
# Falls back to SQLite for local development.
_DATABASE_URL = os.environ.get('DATABASE_URL')
if _DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(_DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Static files (CSS, JS, images) ───────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'          # collectstatic writes here
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

# ── Media files (user uploads) ────────────────────────────────────────────────
# On Azure App Service the /home directory is persistent, so uploads survive
# restarts. They will NOT survive a fresh code deployment unless you mount
# Azure Files or use Azure Blob Storage (django-storages[azure]).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Security headers (always on) ─────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER   = True   # X-XSS-Protection header
SECURE_CONTENT_TYPE_NOSNIFF = True   # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS             = 'DENY' # X-Frame-Options: no iframes

# ── HTTPS-only cookies (production only — would break local HTTP dev) ─────────
if not DEBUG:
    SESSION_COOKIE_SECURE      = True
    CSRF_COOKIE_SECURE         = True
    SECURE_HSTS_SECONDS        = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
