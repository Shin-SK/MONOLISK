# settings
import os
from pathlib import Path
import dj_database_url


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"   # ← .env で切替

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-^7unv9!08vya=%@1%&&+5hk)*8)-a_5!3&90s09=lncdd5@hwl'

# SECURITY WARNING: don't run with debug turned on in production!

ALLOWED_HOSTS = [
    'monolisk-98ae20a1c14b.herokuapp.com',
    'monolisk.netlify.app',
    'localhost', '127.0.0.1',
]

# Application definition

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

]

DJ_REST_AUTH = {
    "USER_DETAILS_SERIALIZER": "core.serializers.UserDetailSerializer",
    # ※ 他に書く項目があればここに
}

# 管理画面に飛ばしたい場合
LOGIN_REDIRECT_URL = "/admin/"


DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY":    os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}

STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SITE_ID = 1
AUTH_USER_MODEL = 'core.User'

REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'core.serializers.UserDetailSerializer',
}

REST_AUTH = {
    'SIGNUP_FIELDS': {
        'username': {'required': True},
        'email':    {'required': True},
    },
    'LOGIN_FIELD': 'username',
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
    'corsheaders.middleware.CorsMiddleware',
    "django_htmx.middleware.HtmxMiddleware",
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
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