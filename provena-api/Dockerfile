FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

# Development image: includes dev dependencies
FROM base AS development
RUN pip install -e ".[dev]"
COPY . .

# Production image: minimal, no dev tools
FROM base AS production
RUN pip install .
COPY . .
RUN DJANGO_SECRET_KEY=dummy-build-only \
    DATABASE_URL=sqlite:////tmp/build.db \
    REDIS_URL=redis://localhost/0 \
    python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
