"""Database backup to S3 / Cloudflare R2.

Streams a `pg_dump` of the default database through gzip and uploads it to the
configured bucket, then prunes backups older than the retention window. Used by
the daily Celery beat task and the `backup_database` management command.
"""

import gzip
import logging
import os
import shutil
import subprocess  # nosec B404 - pg_dump invoked with a fixed argument list, no shell
import tempfile
from datetime import timedelta

import boto3
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

KEY_PREFIX = "provena-"
KEY_SUFFIX = ".sql.gz"


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
    )


def _bucket() -> str:
    bucket = getattr(settings, "DB_BACKUP_BUCKET_NAME", "") or settings.AWS_STORAGE_BUCKET_NAME
    if not bucket:
        raise RuntimeError(
            "No backup bucket configured: set DB_BACKUP_BUCKET_NAME or AWS_STORAGE_BUCKET_NAME."
        )
    return bucket


def _dump_to_gzip(path: str) -> None:
    """Run pg_dump for the default database and write gzipped output to `path`."""
    db = settings.DATABASES["default"]
    cmd = [
        "pg_dump",
        "--no-owner",
        "--no-privileges",
        "--host",
        str(db.get("HOST") or "localhost"),
        "--port",
        str(db.get("PORT") or 5432),
        "--username",
        str(db["USER"]),
        db["NAME"],
    ]
    env = {**os.environ, "PGPASSWORD": str(db.get("PASSWORD") or "")}

    # stderr goes to an unbounded temp file, not a pipe: draining only stdout
    # while pg_dump blocks writing to a full stderr pipe would deadlock.
    with tempfile.TemporaryFile() as errfile:
        with subprocess.Popen(  # noqa: S603  # nosec B603 - fixed argv, no shell, inputs from settings
            cmd, stdout=subprocess.PIPE, stderr=errfile, env=env
        ) as proc:
            assert proc.stdout is not None
            with gzip.open(path, "wb") as gz:
                shutil.copyfileobj(proc.stdout, gz)
        # Popen.__exit__ has waited, so returncode is set.
        if proc.returncode != 0:
            errfile.seek(0)
            message = errfile.read().decode(errors="replace")
            raise RuntimeError(f"pg_dump failed ({proc.returncode}): {message}")


def create_backup() -> str:
    """Create a compressed database dump, upload it, prune old backups. Returns the S3 key."""
    prefix = getattr(settings, "DB_BACKUP_PREFIX", "backups/")
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    key = f"{prefix}{KEY_PREFIX}{stamp}{KEY_SUFFIX}"
    bucket = _bucket()

    with tempfile.NamedTemporaryFile(suffix=KEY_SUFFIX) as tmp:
        _dump_to_gzip(tmp.name)
        size = os.path.getsize(tmp.name)
        _s3_client().upload_file(tmp.name, bucket, key)

    logger.info("Database backup uploaded: s3://%s/%s (%d bytes)", bucket, key, size)
    prune_old_backups()
    return key


def prune_old_backups() -> int:
    """Delete backups older than the retention window. Returns the number deleted."""
    retention_days = int(getattr(settings, "DB_BACKUP_RETENTION_DAYS", 30))
    prefix = getattr(settings, "DB_BACKUP_PREFIX", "backups/")
    # Only ever touch backups this job created, not other archives that might
    # share the prefix.
    key_prefix = f"{prefix}{KEY_PREFIX}"
    bucket = _bucket()
    cutoff = timezone.now() - timedelta(days=retention_days)

    client = _s3_client()
    stale: list[dict[str, str]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not (key.startswith(key_prefix) and key.endswith(KEY_SUFFIX)):
                continue
            if obj["LastModified"] < cutoff:
                stale.append({"Key": key})

    for i in range(0, len(stale), 1000):
        client.delete_objects(Bucket=bucket, Delete={"Objects": stale[i : i + 1000]})

    if stale:
        logger.info("Pruned %d backup(s) older than %d days", len(stale), retention_days)
    return len(stale)
