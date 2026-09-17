#!/usr/bin/env python3
"""Apply the event-store migrations, in order, exactly once each.

    make migrate
    DATABASE_URL=postgres://app:app@localhost:5433/app python3 apps/service/migrations/apply.py

Deliberately a plain script beside the `.sql` files rather than a module inside the service
package: it runs before anything is installed, it needs nothing from the domain, and keeping it
out of the package means it cannot become somewhere application code imports from.

Also deliberately small rather than a migration framework. What a framework buys is branching,
squashing and generated rollbacks; what this needs is "run these files once, in order, and
record it". The day that stops being enough, replace this file — the `.sql` files and the
ledger table are the part worth keeping.

There are no down migrations. Reversing an event-log schema change is a reviewed operation, and
a rollback that lives next to its migration is a rollback that eventually runs by accident.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

LEDGER = """
  CREATE TABLE IF NOT EXISTS schema_migrations (
    name    TEXT        PRIMARY KEY,
    run_on  TIMESTAMPTZ NOT NULL DEFAULT now()
  )
"""


def migrations(directory: Path) -> list[Path]:
    """Every migration, in lexical order — which the shipped ones' zero-padded numbers and a new one's
    `YYYYMMDDHHMM` stamp both keep, every stamp sorting after every number."""
    return sorted(directory.glob("[0-9]*.sql"))


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print(
            "DATABASE_URL is not set. `make migrate` exports the value from the Makefile; "
            "outside make, copy it from .env.example.",
            file=sys.stderr,
        )
        return 2

    try:
        import psycopg
    except ModuleNotFoundError:
        print(
            "psycopg is not installed. Run `make install` first.",
            file=sys.stderr,
        )
        return 2

    directory = Path(__file__).resolve().parent
    pending = migrations(directory)
    if not pending:
        print("migrate: no migrations to apply")
        return 0

    with psycopg.connect(url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(LEDGER)
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
        connection.commit()

        for migration in pending:
            name = migration.stem
            if name in applied:
                continue
            # One transaction per migration, including its ledger row: a migration that
            # half-applied and still counted as done is the failure mode this exists to
            # prevent. Postgres runs DDL transactionally, so this is a real guarantee.
            try:
                with connection.cursor() as cursor:
                    cursor.execute(migration.read_text())
                    cursor.execute(
                        "INSERT INTO schema_migrations (name) VALUES (%s)", (name,)
                    )
                connection.commit()
            except Exception as error:
                connection.rollback()
                print(f"migrate: {name} failed and was rolled back: {error}", file=sys.stderr)
                return 1
            print(f"migrate: applied {name}")

    print("migrate: up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
