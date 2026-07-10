from pathlib import Path

import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(BASE_DIR / ".env")

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
    "channels",
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
    "apps.disputes",
]

INSTALLED_APPS = ["daphne", *DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

# SessionMiddleware and CsrfViewMiddleware are required by the Django admin
# interface. They have no effect on REST API security: every API endpoint
# authenticates via JWT Bearer tokens (JWTAuthentication), so the session
# cookie is never read and CSRF tokens are never checked for API requests.
# The HttpOnly refresh-token cookie (provena_rt) uses SameSite=Lax, which
# prevents cross-site POST requests from carrying the cookie — CSRF on the
# token-refresh endpoint is mitigated by the browser's SameSite policy rather
# than by CsrfViewMiddleware.
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
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL")]},
    }
}

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
        {
            "name": "Payments (Buyer)",
            "description": "Create Stripe PaymentIntents and view payment history",
        },
        {
            "name": "Payments (Supplier)",
            "description": "Supplier payout ledger: view pending, processing, and paid payouts",
        },
        {"name": "Admin: Payments", "description": "Admin payment and payout oversight"},
        {"name": "Marketplace: Cart", "description": "Buyer shopping cart management"},
        {"name": "Marketplace: Wishlist", "description": "Buyer saved items"},
        {
            "name": "Marketplace: Reviews",
            "description": "Product reviews: submit, list approved; verified-purchase badge auto-applied",
        },
        {
            "name": "Admin: Marketplace",
            "description": "Admin review moderation: approve or delete",
        },
        {
            "name": "Notifications",
            "description": "In-app notification feed: list, mark read, delete",
        },
        {
            "name": "Admin: Analytics",
            "description": "Admin-only reports: sales, revenue trends, top products, supplier performance, inventory health, reviews, payouts",
        },
        {
            "name": "Analytics (Supplier)",
            "description": "Supplier self-service analytics: own revenue summary and payout breakdown",
        },
    ],
}

NOTIFICATION_BACKENDS = [
    "apps.notifications.backends.InAppBackend",
    "apps.notifications.backends.EmailBackend",
]

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
        "apps.accounts.throttling.BuyerRateThrottle",
        "apps.accounts.throttling.SupplierRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "supplier": "2000/hour",
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
CELERY_BEAT_SCHEDULE = {
    "release-expired-cart-reservations": {
        "task": "apps.marketplace.tasks.release_expired_cart_reservations",
        "schedule": 300,  # every 5 minutes
    },
    "check-low-stock-levels": {
        "task": "apps.inventory.tasks.check_low_stock_levels",
        "schedule": 86400,  # daily
    },
    "check-lot-expiry": {
        "task": "apps.inventory.tasks.check_lot_expiry",
        "schedule": 86400,  # daily
        "kwargs": {"days_ahead": 3},
    },
    "auto-escalate-overdue-disputes": {
        "task": "apps.disputes.tasks.auto_escalate_overdue_disputes",
        "schedule": 3600,  # hourly
    },
    "purge-expired-data-exports": {
        "task": "apps.accounts.tasks.purge_expired_exports",
        "schedule": 3600,  # hourly
    },
}

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
PLATFORM_FEE_PERCENT = env("PLATFORM_FEE_PERCENT", default="10")

# S3 / Cloudflare R2 (overridden in production.py with real credentials)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-2")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = "private"

# Frontend
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.resend.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="resend")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="onboarding@resend.dev")

# CORS - overridden in environment-specific settings
CORS_ALLOWED_ORIGINS: list[str] = []
CORS_ALLOW_CREDENTIALS = True

# Refresh-token HttpOnly cookie
REFRESH_COOKIE_NAME = "provena_rt"
REFRESH_COOKIE_SAMESITE = "Lax"
REFRESH_COOKIE_SECURE = False  # Overridden to True in production

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
