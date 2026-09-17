"""The service container one feature's integration job needs, and how to wait for it.

Split out of `ci_workflows.py` for the reason `native_commands.py` is split out of `makefile.py`: this is
most of that job's bytes and none of its shape. Which image, which environment, and what "ready" means are
facts about a product — searched and pinned once — so they are written per feature; *whether* an
integration job is emitted at all is a trait the selection answers, over in `ci_workflows.py`.

Two chunks per feature rather than one, because the generic middle of the job sits between them: the `env:`
and `services:` blocks belong to the job header, and the readiness probe runs after the install step.
"""
from __future__ import annotations

CI_SERVICES = {
    "postgres": {
        "service": """    env:
      # Service label and the service's own port. The Makefile's `?=` default stays localhost:5433, which
      # is where `make services-up` puts it locally; nothing derives one from the other.
      DATABASE_URL: postgres://app:app@postgres:5432/app
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app
        options: >-
          --health-cmd "pg_isready -U app -d app"
          --health-interval 2s
          --health-timeout 3s
          --health-retries 20
""",
        "readiness": """
      # A GitHub-hosted runner blocks the job until the service's --health-cmd passes, but that is the
      # scheduler's promise rather than Docker's: another runner may start the job while Postgres is still
      # binding. `shell: bash` is load-bearing — a job with `container:` otherwise runs its steps under
      # plain `sh`, where /dev/tcp is not a feature and silently does nothing instead of failing, so the
      # probe would report "never reachable" whether or not it is.
      - name: Wait for Postgres
        shell: bash
        run: |
          for _ in $(seq 1 60); do
            (exec 3<>/dev/tcp/postgres/5432) 2>/dev/null && exit 0
            sleep 0.5
          done
          echo 'postgres did not accept connections within 30s' >&2
          exit 1
""",
    },
}
