import environ

from .base import *  # noqa: F403

env = environ.Env()

DEBUG = True

# "api" is the Docker service name, so in-network scrapers (Prometheus hitting
# api:8000/metrics) and other services pass the Host check.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api"]

CORS_ALLOWED_ORIGINS = [
    # Nginx single origin (scripts/up.sh serves the app here on port 80).
    "http://localhost",
    "http://127.0.0.1",
    # Next.js dev server reached directly.
    "http://localhost:3000",
    "http://localhost:3001",
]

# Use local filesystem for media in development
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

# Disable throttling in development
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
}

# Use local memory cache in development/test so Redis is not required
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
