# config/settings.py
from pathlib import Path
import environ, cloudinary, dj_database_url, os

BASE_DIR = Path(__file__).resolve().parent.parent     # ★ 先に定義

env = environ.Env()
env.read_env(BASE_DIR / ".env")                      # ★ 絶対パス指定

DEBUG = env.bool("DJANGO_DEBUG", default=True)

cloudinary.config(
	cloud_name = env("CLOUDINARY_CLOUD_NAME"),
	api_key    = env("CLOUDINARY_API_KEY"),
	api_secret = env("CLOUDINARY_API_SECRET"),
	secure     = True,
)

# DEBUG=True なら localhost 系を保証
if DEBUG:
	# 開発は何でも通す（セキュリティは本番で担保）
	ALLOWED_HOSTS = ["*"]
else:
	# 本番は .env で明示
	ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

SECRET_KEY = 'django-insecure-^7unv9!08vya=%@1%&&+5hk)*8)-a_5!3&90s09=lncdd5@hwl'


INSTALLED_APPS = [
    # "jazzmin",
    "django.contrib.postgres",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',      # allauth 必須
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework.authtoken',  # dj-rest-auth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'dj_rest_auth',
    'corsheaders',
    'django_htmx',
    'import_export',
    'django_filters',
    "cloudinary",
    "cloudinary_storage",
    'dal',              # ← 追加
    'dal_select2',      # ← 追加（Select2 フロント）
    "django_extensions",

    'core.apps.CoreConfig',
    'accounts',
    'billing',

]


AUTH_USER_MODEL = 'accounts.User'

REST_AUTH_REGISTER_SERIALIZERS = {
    'REGISTER_SERIALIZER': 'accounts.forms.MyRegisterSerializer',
}


# 管理画面に飛ばしたい場合
LOGIN_REDIRECT_URL = "/admin/"


DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

cloudinary.config(
    cloud_name = env('CLOUDINARY_CLOUD_NAME'),
    api_key    = env('CLOUDINARY_API_KEY'),
    api_secret = env('CLOUDINARY_API_SECRET'),
    secure     = True,
)


STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SITE_ID = 1


REST_AUTH = {
    # 既存
    'SIGNUP_FIELDS': {
        'username': {'required': True},
        'email':    {'required': True},
    },
    'LOGIN_FIELD': 'username',

    # 追記／統合
    'LOGIN_SERIALIZER'       : 'accounts.serializers.LoginWithStoreSerializer',
    'USER_DETAILS_SERIALIZER': 'accounts.serializers.UserDetailsWithStoreSerializer',
}
# allauth のログインは username のみ許可
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_REQUIRED        = True
ACCOUNT_USERNAME_REQUIRED     = True
ACCOUNT_EMAIL_VERIFICATION    = "none"     # ← 面倒を避けるなら


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",  # 全 API をデフォルト締め
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',   # ★ 追加
    ),
    # "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    # "PAGE_SIZE": 30,           # お好みで
}
REST_SESSION_LOGIN = False 

# 本番だけ締める場合
if not DEBUG:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (
        "rest_framework.permissions.IsAuthenticated",
    )

# ---------- CORS ----------
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE    = not DEBUG
SESSION_COOKIE_SAMESITE = 'None' if not DEBUG else 'Lax'
CSRF_COOKIE_SAMESITE    = 'None' if not DEBUG else 'Lax'
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'https://monolisk.netlify.app',
    'http://localhost:5173',
]
CSRF_TRUSTED_ORIGINS = [
    'https://monolisk.netlify.app',
    'http://localhost:5173',
]

MIDDLEWARE = [
    'accounts.middleware.StoreFromPathMiddleware',

    'corsheaders.middleware.CorsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'billing.middleware.AttachStoreMiddleware',
    
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],   # ← 追加
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

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


WSGI_APPLICATION = 'config.wsgi.application'

# ------- DB -------
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
            ssl_require=True,      # 本番だけ
        )
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'
USE_TZ    = True

USE_I18N = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"




LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,        # ← 既存を殺さない
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    # ――― ここを足す ―――
    "loggers": {
        "django.request": {                   # 500 を出すロガー
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,               # ルートに渡さず直吐き
        },
    },
}



CASH_ALERT_THRESHOLD = 200_000

DEFAULT_STORE_ID = 1
STORE_MODEL = 'billing.Store'

BILL_PL_DEFAULT_STORE = 1