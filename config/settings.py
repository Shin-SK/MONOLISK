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

# ── Hosts / CORS / CSRF ──────────────────────
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[".monolisk-app.com"])

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"
CSRF_COOKIE_SAMESITE = "None" if not DEBUG else "Lax"

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://monolisk-app.com",
    "https://www.monolisk-app.com",
    "https://monolisk-stg.netlify.app",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/([a-z0-9-]+\.)?monolisk-app\.com$",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://monolisk-app.com",
    "https://*.monolisk-app.com",
    "https://api.monolisk-app.com",
    "https://monolisk-stg.netlify.app",
    "https://monolisk-stg-192515f15c7f.herokuapp.com",
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-store-id",   # ← これを許可
    "x-silent",     # ← 既存で使っているなら許可（meta→headerの互換向け）
    "cache-control",
    "pragma",          # ← これが今足りない
    "expires",         # ← 念のため一緒に許可（no-cache系で付くことがある）
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG


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
# ・DEFAULT_STORE_ID / BILL_PL_DEFAULT_STORE は撤廃（Store-Locked原則）
# ・サブドメイン→店舗解決は、後日 middleware を導入してもOK

PL_DRINK_CATEGORY_CODES = {"cast-drink"}   # 今はこれだけ
PL_DRINK_ITEM_PREFIXES  = set()            # 使わない