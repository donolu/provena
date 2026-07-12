FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# libpq-dev + gcc for building Python deps; postgresql-client-16 provides the
# pg_dump used by the automated database backups (must match the PG16 server,
# so it comes from the PGDG apt repo rather than Debian's default v15).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    gnupg \
    ca-certificates \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y --auto-remove curl gnupg \
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
