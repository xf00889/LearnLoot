from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def build_pg_environment(database: dict) -> dict[str, str]:
    child_env = os.environ.copy()
    mapping = {
        "PGHOST": database.get("HOST"),
        "PGPORT": database.get("PORT"),
        "PGUSER": database.get("USER"),
        "PGPASSWORD": database.get("PASSWORD"),
    }
    for key, value in mapping.items():
        if value not in (None, ""):
            child_env[key] = str(value)

    options = database.get("OPTIONS") or {}
    option_mapping = {
        "sslmode": "PGSSLMODE",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "sslrootcert": "PGSSLROOTCERT",
    }
    for option_name, env_name in option_mapping.items():
        value = options.get(option_name)
        if value not in (None, ""):
            child_env[env_name] = str(value)

    return child_env


class Command(BaseCommand):
    help = "Create a PostgreSQL custom-format backup without putting the password on the command line."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--pg-dump", default="")

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        engine = str(database.get("ENGINE") or "")
        if "postgresql" not in engine:
            raise CommandError("backup_postgres supports PostgreSQL only.")

        executable = str(options["pg_dump"] or "").strip() or shutil.which("pg_dump")
        if not executable:
            raise CommandError("pg_dump was not found. Add PostgreSQL client tools to PATH or use --pg-dump.")

        output = Path(options["output"]).expanduser().resolve()
        if output.exists() and not options["overwrite"]:
            raise CommandError(f"Refusing to overwrite existing backup: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)

        partial = output.with_name(output.name + ".partial")
        if partial.exists():
            raise CommandError(
                f"Refusing to overwrite existing partial backup: {partial}"
            )

        database_name = str(database.get("NAME") or "").strip()
        if not database_name:
            raise CommandError("Database NAME is empty.")

        command = [
            executable,
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--file",
            str(partial),
            database_name,
        ]
        try:
            result = subprocess.run(
                command,
                env=build_pg_environment(database),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise CommandError(
                    "pg_dump failed. Review the PostgreSQL client/server logs; credentials were not printed."
                )

            if not partial.exists() or partial.stat().st_size <= 0:
                raise CommandError(
                    "pg_dump reported success but the backup file is empty."
                )

            os.replace(partial, output)
        finally:
            if partial.exists():
                partial.unlink()

        self.stdout.write(f"BACKUP_PATH={output}")
        self.stdout.write(f"BACKUP_BYTES={output.stat().st_size}")
        self.stdout.write("PHASE10_POSTGRES_BACKUP=PASS")
