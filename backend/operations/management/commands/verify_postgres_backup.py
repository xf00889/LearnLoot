from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify that pg_restore can read a PostgreSQL custom-format backup."

    def add_arguments(self, parser):
        parser.add_argument("backup")
        parser.add_argument("--pg-restore", default="")

    def handle(self, *args, **options):
        backup = Path(options["backup"]).expanduser().resolve()
        if not backup.is_file() or backup.stat().st_size <= 0:
            raise CommandError("Backup file does not exist or is empty.")

        executable = str(options["pg_restore"] or "").strip() or shutil.which("pg_restore")
        if not executable:
            raise CommandError("pg_restore was not found. Add PostgreSQL client tools to PATH or use --pg-restore.")

        result = subprocess.run(
            [executable, "--list", str(backup)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise CommandError("pg_restore could not read the backup archive.")

        self.stdout.write("PHASE10_POSTGRES_BACKUP_VERIFY=PASS")
