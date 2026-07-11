import environ
import sentry_sdk

from .base import *  # noqa: F403

env = environ.Env()

DEBUG = False

# Internal probes (the container healthcheck in docker-compose.yml, and any
# load-balancer readiness check) reach the app over the pod-local loopback,
# so Host: 127.0.0.1 must pass ALLOWED_HOSTS even when DJANGO_ALLOWED_HOSTS
# only lists public hostnames. Loopback is not a useful Host-spoofing vector
# (an injected 127.0.0.1 link is worthless to an attacker), so always allow it.
ALLOWED_HOSTS += ["127.0.0.1", "localhost"]  # noqa: F405

# Security
SECURE_SSL_REDIRECT = True
# Internal probes/scrapers (Prometheus, load-balancer health checks) reach the
# API over plain HTTP inside the network; exempt those paths from the HTTPS
# redirect so they are not 301'd. The internal scrape hostname must still be in
# DJANGO_ALLOWED_HOSTS.
SECURE_REDIRECT_EXEMPT = [r"^metrics$", r"^api/v1/health/$"]
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
REFRESH_COOKIE_SECURE = True
CART_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
# CORS_ALLOW_CREDENTIALS is set to True in base.py to allow the browser to
# send the HttpOnly refresh-token cookie on cross-origin requests to /auth/refresh/.
# It must always be paired with CORS_ALLOWED_ORIGINS (never CORS_ALLOW_ALL_ORIGINS).

# S3 / Cloudflare R2 file storage
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-2")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = "private"

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@provena.io")

# Sentry
sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="production",
)
