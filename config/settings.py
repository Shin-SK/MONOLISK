# config/settings.py
from pathlib import Path
import os
import environ
import dj_database_url
import cloudinary
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

# ── env ─────────────────────────────────────────────────────────────
env = environ.Env()

env_file = BASE_DIR / (".env.local" if os.getenv("USE_LOCAL_ENV") == "1" else ".env")
env.read_env(env_file)

DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = env("SECRET_KEY", default=None) or env("DJANGO_SECRET_KEY", default="django-insecure-dev-key")

# ── Cloudinary ──────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = env("CLOUDINARY_CLOUD_NAME"),
    api_key    = env("CLOUDINARY_API_KEY"),
    api_secret = env("CLOUDINARY_API_SECRET"),
    secure     = True,
)

# ── Hosts / CORS / CSRF ─────────────────────────────────────────────
# ローカル開発 & Heroku/Netlify 兼用のデフォルト
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "api",
    "monolisk-98ae20a1c14b.herokuapp.com",
    "monolisk.netlify.app",
]

# 必要なら本番だけ env で上書き
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    hosts = env.list("ALLOWED_HOSTS", default=[])
    if hosts:
        ALLOWED_HOSTS = hosts

# クロスサイト Cookie（Netlify↔Heroku）前提で secure/samesite をENVで調整可
CROSS_SITE = env.bool("CROSS_SITE_COOKIES", default=not DEBUG)
SESSION_COOKIE_SECURE   = env.bool("SESSION_COOKIE_SECURE", default=CROSS_SITE or not DEBUG)
CSRF_COOKIE_SECURE      = env.bool("CSRF_COOKIE_SECURE",  default=CROSS_SITE or not DEBUG)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default=("None" if CROSS_SITE else "Lax"))
CSRF_COOKIE_SAMESITE    = env("CSRF_COOKIE_SAMESITE",    default=("None" if CROSS_SITE else "Lax"))

from corsheaders.defaults import default_headers
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
CORS_ALLOWED_ORIGINS   = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:5173", "http://127.0.0.1:5173"
])
CSRF_TRUSTED_ORIGINS   = env.list("CSRF_TRUSTED_ORIGINS", default=[
    "http://localhost:5173", "http://127.0.0.1:5173"
])

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/([a-z0-9-]+\.)?monolisk-app\.com$",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT     = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)


# ── Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
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

REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'billing.serializers_user_details.UserDetailsWithAvatarSerializer',
    'LOGIN_SERIALIZER':       'accounts.serializers.LoginWithStoreSerializer',
}

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

if os.getenv('REDIS_URL'):
	# 本番など Redis があるとき
	CACHES = {
		'default': {
			'BACKEND': 'django_redis.cache.RedisCache',
			'LOCATION': os.environ['REDIS_URL'],
			'OPTIONS': {
				'CLIENT_CLASS': 'django_redis.client.DefaultClient',
				'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
			}
		}
	}
else:
	# 開発はプロセス内メモリ（Redis不要）
	CACHES = {
		'default': {
			'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
			'LOCATION': 'monolisk-dev',
		}
	}


# ── Middleware ──────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
	'django.middleware.gzip.GZipMiddleware',
	'django.middleware.http.ConditionalGetMiddleware',
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
    "USER_DETAILS_SERIALIZER": "billing.serializers_user_details.UserDetailsWithAvatarSerializer",
    "TOKEN_SERIALIZER":        "accounts.serializers.TokenWithStoreSerializer",
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
db_url = env("DATABASE_URL", default=None)

if db_url:
    # DATABASE_URL があれば、DEBUGでも常にそれを使う（Postgres推奨）
    DATABASES = {
        "default": dj_database_url.parse(db_url, conn_max_age=600)
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=600, ssl_require=True)
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
# ・サブドメイン→店舗解決は、後日 middleware を導入してもOK

PL_DRINK_CATEGORY_CODES = {"cast-drink"}   # 今はこれだけ
PL_DRINK_ITEM_PREFIXES  = set()            # 使わない