"""Load the Celery app when Django starts.

Without this import the Celery application in ``config.celery`` is only created
in the worker/beat processes (started with ``-A config.celery``). The web and
management-command processes would then fall back to Celery's default app and
broker, so any ``shared_task().delay()`` (search indexing, data exports, payout
triggers, ...) fails to reach Redis. Importing it here makes every process use
the configured broker.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
