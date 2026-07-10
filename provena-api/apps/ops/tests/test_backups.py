import gzip
import io
import re
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.ops import backups


@pytest.fixture
def backup_settings(settings):
    settings.DB_BACKUP_BUCKET_NAME = "test-backups"
    settings.DB_BACKUP_PREFIX = "backups/"
    settings.DB_BACKUP_RETENTION_DAYS = 30
    return settings


class TestCreateBackup:
    @patch("apps.ops.backups.prune_old_backups")
    @patch("apps.ops.backups._dump_to_gzip")
    @patch("apps.ops.backups._s3_client")
    def test_uploads_with_timestamped_key_and_prunes(
        self, mock_client, mock_dump, mock_prune, backup_settings
    ):
        s3 = MagicMock()
        mock_client.return_value = s3

        key = backups.create_backup()

        assert re.fullmatch(r"backups/provena-\d{8}T\d{6}Z\.sql\.gz", key)
        mock_dump.assert_called_once()
        # upload_file(local_path, bucket, key)
        args = s3.upload_file.call_args.args
        assert args[1] == "test-backups"
        assert args[2] == key
        mock_prune.assert_called_once()

    @patch("apps.ops.backups._dump_to_gzip")
    @patch("apps.ops.backups._s3_client")
    def test_raises_when_no_bucket_configured(self, mock_client, mock_dump, settings):
        settings.DB_BACKUP_BUCKET_NAME = ""
        settings.AWS_STORAGE_BUCKET_NAME = ""
        with pytest.raises(RuntimeError, match="No backup bucket configured"):
            backups.create_backup()

    @patch("apps.ops.backups._dump_to_gzip")
    @patch("apps.ops.backups._s3_client")
    def test_falls_back_to_storage_bucket(self, mock_client, mock_dump, settings):
        settings.DB_BACKUP_BUCKET_NAME = ""
        settings.AWS_STORAGE_BUCKET_NAME = "fallback-bucket"
        s3 = MagicMock()
        mock_client.return_value = s3
        with patch("apps.ops.backups.prune_old_backups"):
            backups.create_backup()
        assert s3.upload_file.call_args.args[1] == "fallback-bucket"


class TestPruneOldBackups:
    def _page(self, objects):
        return {"Contents": objects}

    @patch("apps.ops.backups._s3_client")
    def test_deletes_only_stale_sql_gz(self, mock_client, backup_settings):
        now = timezone.now()
        old = now - timedelta(days=40)
        recent = now - timedelta(days=5)
        s3 = MagicMock()
        s3.get_paginator.return_value.paginate.return_value = [
            self._page(
                [
                    {"Key": "backups/provena-old.sql.gz", "LastModified": old},
                    {"Key": "backups/provena-recent.sql.gz", "LastModified": recent},
                    {"Key": "backups/notes.txt", "LastModified": old},  # ignored: wrong suffix
                ]
            )
        ]
        mock_client.return_value = s3

        deleted = backups.prune_old_backups()

        assert deleted == 1
        s3.delete_objects.assert_called_once_with(
            Bucket="test-backups",
            Delete={"Objects": [{"Key": "backups/provena-old.sql.gz"}]},
        )

    @patch("apps.ops.backups._s3_client")
    def test_no_delete_when_all_recent(self, mock_client, backup_settings):
        s3 = MagicMock()
        s3.get_paginator.return_value.paginate.return_value = [
            self._page([{"Key": "backups/provena-recent.sql.gz", "LastModified": timezone.now()}])
        ]
        mock_client.return_value = s3

        assert backups.prune_old_backups() == 0
        s3.delete_objects.assert_not_called()


class TestDumpToGzip:
    @patch("apps.ops.backups.subprocess.Popen")
    def test_writes_gzipped_dump_and_builds_pg_dump_command(self, mock_popen, tmp_path):
        proc = MagicMock()
        proc.stdout = io.BytesIO(b"-- pg dump output")
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        mock_popen.return_value.__enter__.return_value = proc

        dest = str(tmp_path / "out.sql.gz")
        backups._dump_to_gzip(dest)

        with gzip.open(dest, "rb") as f:
            assert f.read() == b"-- pg dump output"
        cmd = mock_popen.call_args.args[0]
        assert cmd[0] == "pg_dump"
        assert "--no-owner" in cmd and "--no-privileges" in cmd

    @patch("apps.ops.backups.subprocess.Popen")
    def test_raises_on_nonzero_exit(self, mock_popen, tmp_path):
        proc = MagicMock()
        proc.stdout = io.BytesIO(b"")
        proc.communicate.return_value = (b"", b"connection refused")
        proc.returncode = 1
        mock_popen.return_value.__enter__.return_value = proc

        with pytest.raises(RuntimeError, match="pg_dump failed"):
            backups._dump_to_gzip(str(tmp_path / "out.sql.gz"))


class TestS3Client:
    @patch("apps.ops.backups.boto3.client")
    def test_passes_endpoint_url_for_r2(self, mock_boto, settings):
        settings.AWS_S3_ENDPOINT_URL = "http://minio:9000"
        backups._s3_client()
        assert mock_boto.call_args.kwargs["endpoint_url"] == "http://minio:9000"

    @patch("apps.ops.backups.boto3.client")
    def test_empty_endpoint_becomes_none(self, mock_boto, settings):
        settings.AWS_S3_ENDPOINT_URL = ""
        backups._s3_client()
        assert mock_boto.call_args.kwargs["endpoint_url"] is None


class TestBackupTask:
    @patch("apps.ops.backups.create_backup", return_value="backups/provena-x.sql.gz")
    def test_task_delegates_to_create_backup(self, mock_create):
        from apps.ops.tasks import backup_database

        assert backup_database() == "backups/provena-x.sql.gz"
        mock_create.assert_called_once()


class TestBackupCommand:
    @patch(
        "apps.ops.management.commands.backup_database.create_backup",
        return_value="backups/provena-cmd.sql.gz",
    )
    def test_command_reports_uploaded_key(self, mock_create):
        out = io.StringIO()
        call_command("backup_database", stdout=out)
        assert "backups/provena-cmd.sql.gz" in out.getvalue()
        mock_create.assert_called_once()
