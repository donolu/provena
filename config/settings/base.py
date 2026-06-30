from pathlib import Path

import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "storages",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.suppliers",
    "apps.catalogue",
    "apps.inventory",
    "apps.orders",
    "apps.payments",
    "apps.marketplace",
    "apps.notifications",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# OpenAPI docs
SPECTACULAR_SETTINGS = {
    "TITLE": "Provena API",
    "DESCRIPTION": (
        "REST API for the Provena supply chain and marketplace platform. "
        "All endpoints are versioned under `/api/v1/`. "
        "Authentication uses JWT Bearer tokens (15-minute access, 30-day rotating refresh)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "ENUM_NAME_OVERRIDES": {
        "SupplierStatusEnum": "apps.suppliers.models.SupplierStatus",
        "DocumentStatusEnum": "apps.suppliers.models.DocumentStatus",
        "DocumentTypeEnum": "apps.suppliers.models.DocumentType",
    },
    "TAGS": [
        {"name": "Authentication", "description": "Register, login, logout, token refresh"},
        {"name": "User Profile", "description": "View and update the authenticated user's profile"},
        {"name": "Password Reset", "description": "Self-service password reset via email"},
        {"name": "Two-Factor Authentication", "description": "TOTP setup, enable, and disable"},
        {"name": "Suppliers (Public)", "description": "Publicly readable supplier data"},
        {
            "name": "Suppliers (Supplier)",
            "description": "Supplier self-service profile and documents",
        },
        {"name": "Stripe Connect", "description": "Stripe Connect onboarding for supplier payouts"},
        {"name": "Admin: Suppliers", "description": "Admin-only supplier management"},
        {"name": "Admin: KYC Documents", "description": "Admin-only document review queue"},
        {
            "name": "Inventory (Supplier)",
            "description": "Supplier stock management: receive lots, adjust quantities, view audit log",
        },
        {
            "name": "Admin: Inventory",
            "description": "Admin-only inventory overview and low-stock monitoring",
        },
        {
            "name": "Orders (Buyer)",
            "description": "Place orders, view order history, cancel, raise disputes",
        },
        {
            "name": "Orders (Supplier)",
            "description": "Supplier order fulfilment: confirm, dispatch, deliver",
        },
        {"name": "Admin: Orders", "description": "Admin order management and dispute resolution"},
    ],
}

# DRF
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.provena_exception_handler",
}

# JWT
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Celery
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

# Stripe
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# Frontend
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# CORS - overridden in environment-specific settings
CORS_ALLOWED_ORIGINS: list[str] = []

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "django.utils.log.ServerFormatter",
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
