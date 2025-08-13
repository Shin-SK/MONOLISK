# config/settings.py
from pathlib import Path
import os
import environ
import dj_database_url
import cloudinary

BASE_DIR = Path(__file__).resolve().parent.parent

# ── env ─────────────────────────────────────────────────────────────
env = environ.Env()
env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-key")

# ── Cloudinary ──────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = env("CLOUDINARY_CLOUD_NAME"),
    api_key    = env("CLOUDINARY_API_KEY"),
    api_secret = env("CLOUDINARY_API_SECRET"),
    secure     = True,
)

# ── Hosts / CORS / CSRF（{store}.monolisk.app）──────────────────────
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    # 既定でサブドメイン含め許可（必要なら .env で上書き）
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[".monolisk.app"])

SESSION_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_SECURE      = not DEBUG
SESSION_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"
CSRF_COOKIE_SAMESITE    = "None" if not DEBUG else "Lax"


# ---------- CORS / CSRF ----------
CORS_ALLOW_CREDENTIALS = True

# 個別ドメイン
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'https://monolisk.app',
    'https://www.monolisk.app',
]

# ワイルドカードサブドメイン対応
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https:\/\/[A-Za-z0-9-]+\.monolisk\.app$',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'https://monolisk.app',
    'https://*.monolisk.app',   # DjangoはワイルドカードOK
]


# ── Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # "jazzmin",
    "django.contrib.postgres",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",

    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "dj_rest_auth",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",

    "corsheaders",
    "django_htmx",
    "import_export",
    "cloudinary",
    "cloudinary_storage",
    "dal",
    "dal_select2",
    "django_extensions",

    # "core.apps.CoreConfig",
    "accounts",
    "billing",
]

SITE_ID = 1
AUTH_USER_MODEL = "accounts.User"

REST_AUTH_REGISTER_SERIALIZERS = {
    "REGISTER_SERIALIZER": "accounts.forms.MyRegisterSerializer",
}

LOGIN_REDIRECT_URL = "/admin/"

# ── Storage / Static ────────────────────────────────────────────────
STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Middleware ──────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",

    "billing.middleware.AttachStoreMiddleware",   # ← 認証の後に置く
    "django_htmx.middleware.HtmxMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── REST Framework / Auth ───────────────────────────────────────────
REST_AUTH = {
    "SIGNUP_FIELDS": {
        "username": {"required": True},
        "email":    {"required": True},
    },
    "LOGIN_FIELD": "username",
    "LOGIN_SERIALIZER":        "accounts.serializers.LoginWithStoreSerializer",
    "USER_DETAILS_SERIALIZER": "accounts.serializers.UserDetailsWithStoreSerializer",
}
ACCOUNT_LOGIN_METHODS     = ["username"]
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "none"
REST_USE_JWT = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DATETIME_INPUT_FORMATS": [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "iso-8601",
    ],
}
REST_SESSION_LOGIN = False

# ── DB ───────────────────────────────────────────────────────────────
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            ssl_require=True,
        )
    }

# ── i18n/tz ──────────────────────────────────────────────────────────
LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_TZ = True
USE_I18N = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Logging ──────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# ── 補足 ─────────────────────────────────────────────────────────────
# ・DEFAULT_STORE_ID / BILL_PL_DEFAULT_STORE は撤廃（Store-Locked原則）
# ・サブドメイン→店舗解決は、後日 middleware を導入してもOK
