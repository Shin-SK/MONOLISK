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
    "jazzmin",
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

    'core.apps.CoreConfig',
    "jazzmin_settings",
    "jazzmin_hide.apps.JazzminHideConfig", 
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
USE_TZ    = False

USE_I18N = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# jazzmin

# ===========================================
#  Jazzmin ― 完全版設定（コピー＆ペースト用）
# ===========================================
JAZZMIN_SETTINGS = {
    # ─ サイト基本情報 ───────────────────────
    "site_title":   "管理者【MONOLISK】",
    "site_brand":   "MONOLISK",
    "site_header":  "MONOLISK 管理",
    "site_logo":    "img/logo.webp",          # static 配下（collectstatic 後のパス）
    "welcome_sign": "ようこそ MONOLISK へ",
    "copyright":    "MONOLISK",

    #──────── サイドバー完全カスタム ────────
    # ─ サイドバー全体を完全手書きで制御 ────
    "navigation_expanded": False,             # 常に折りたたみ開始
    "hide_apps": [],   # core 標準ツリーを丸ごと隠す
    "order_with_respect_to": [
        "core",            # メイン（Reservation, Customer …）
        "jazzmin_hide",    # その他 ← ここに proxy が並ぶ
        "jazzmin_settings",
        "auth",            # ここは jazzmin が自動で作る “アカウント” 親
    ],

    "side_menu": [
        {
            "app": "core",
            "label": "メイン",
            "icon": "fa fa-home",
            "models": [
                {"model": "core.reservation", "label": "予約",        "icon": "fa fa-calendar-check"},
                {"model": "core.customer",    "label": "顧客",        "icon": "fa fa-users"},
                {"model": "core.option",      "label": "オプション",  "icon": "fa fa-tasks"},
                {"model": "core.castprofile", "label": "キャスト情報","icon": "fa fa-star"},
            ],
        },
        {
            "app": "jazzmin_hide",
            "label": "その他",
            "icon": "fa fa-ellipsis-h",
            "models": "*"         # ← proxy 全部自動で並ぶ
        },
        "-",                      # 仕切り線
        {"app": "jazzmin_settings", "label": "設定",   "icon": "fa fa-cogs"},
        {"app": "auth",            "label": "ユーザー","icon": "fa fa-user-shield"},
    ],

    # 元モデルは非表示
    "hide_models": [
        "core.Store", "core.Rank", "core.Course", "core.RankCourse",
        "core.GroupOptionPrice", "core.Driver", "core.CashFlow",
        "core.ReservationCast", "core.ReservationCharge",
        "core.CastCoursePrice", "core.CastOption",
        "core.Performer",                 # Performer も “メイン外” ならここに
        # Django 標準など
        "auth.Group", "auth.Permission", "sites.Site",
    ],

    # アイコンを追加（無い物だけ）
    "icons": {
        # …既存アイコン…
        "jazzmin_hide.storeproxy":            "fa fa-store",
        "jazzmin_hide.rankproxy":             "fa fa-award",
        "jazzmin_hide.courseproxy":           "fa fa-clock",
        "jazzmin_hide.rankcourseproxy":       "fa fa-money-bill",
        "jazzmin_hide.groupoptionpriceproxy": "fa fa-users",
        "jazzmin_hide.driverproxy":           "fa fa-id-badge",
        "jazzmin_hide.cashflowproxy":         "fa fa-coins",
        "jazzmin_hide.reservationcastproxy":  "fa fa-user-friends",
        "jazzmin_hide.reservationchargeproxy":"fa fa-yen-sign",
        "jazzmin_hide.castcoursepriceproxy":  "fa fa-dollar-sign",
        "jazzmin_hide.castoptionproxy":       "fa fa-tag",
    },

    # カスタム CSS / JS
    "custom_css": "css/jazzmin_custom.css",
    # "custom_js":  "js/admin_extra.js",
}




JAZZMIN_UI_TWEAKS = {
    "theme": "lux",
    "sidebar": "sidebar-light-primary",
}


LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "ERROR"},
}