import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = int(os.environ.get("DEBUG", default=0))
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(" ")

GRAPHENE = {"SCHEMA": "dictionary_graph.schema.schema"}

SITE_ID = 1

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "django.contrib.sitemaps",
    "dictionary",
    "django.contrib.admin",
    "dictionary_graph",
    "graphene_django",
    "widget_tweaks",
    "djcelery_email",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "dictionary.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "dictionary.middleware.users.NoviceActivityMiddleware",
    "dictionary.middleware.frontend.MobileDetectionMiddleware",
    "dictionary.middleware.frontend.LeftFrameMiddleware",
]

ROOT_URLCONF = "djdict.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dictionary.utils.context_processors.header_categories",
                "dictionary.utils.context_processors.left_frame_fallback",
            ],
        },
    },
]

WSGI_APPLICATION = "djdict.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE"),
        "NAME": os.environ.get("SQL_DATABASE"),
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD"),
        "HOST": os.environ.get("SQL_HOST"),
        "PORT": os.environ.get("SQL_PORT"),
    }
}


EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
CELERY_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


REDIS_URL = "redis://redis:6379/1"
CELERY_BROKER_URL = REDIS_URL
CELERY_EMAIL_TASK_CONFIG = {"default_retry_delay": 40}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}


LANGUAGE_CODE = "en-us"
LANGUAGE_COOKIE_NAME = "langcode"
LANGUAGE_COOKIE_AGE = 180 * 86400
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGES = (
    ("tr", _("Turkish")),
    ("en", _("English")),
)
USE_I18N = True
USE_L10N = True
USE_TZ = True
TIME_ZONE = "Europe/Istanbul"


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "dictionary.Author"
SESSION_COOKIE_AGE = 1209600
SESSION_ENGINE = "dictionary.backends.sessions.cached_db"
PASSWORD_RESET_TIMEOUT = 86400
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"


STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media"

# Remove this setting if you are creating a brand new database.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
