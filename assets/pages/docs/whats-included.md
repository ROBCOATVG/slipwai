# What's included

{{service-items}}{{frontend-items}}- A monorepo layout with `apps/` for deployables and `packages/` for code shared between them
- `make dev`, `make dev-web` and `make demo` — the app in the foreground or the whole thing in containers,
  plus a `run-the-app` skill describing this project's own run path
- A complete Make target surface for setup, native static checks, tests, integration tests, agent and
  Spec Kit drift, constitution coverage, event-model validation, mutation, adversarial regression tests,
  audit, and CI
- The shared delivery skill catalogue and adapted workflow commands
- An `./init` bootstrap that installs Spec Kit's planning assets on demand
- The toolchain pins a laptop reads, so it runs what CI runs: {{pins}}
- `renovate.json`, so exact pins do not quietly become old exact pins — grouped, weekly, majors held back.
  It does nothing until a bot runs it: the Renovate app on GitHub, or a self-hosted run on a Gitea forge
- `LICENSE`, `SECURITY.md` and a pull-request template. Two of them carry a placeholder on purpose — the
  licence is `All rights reserved` until whoever owns this code decides otherwise, and the security contact
  is the one thing only this project knows. The template names this project's own gates and nothing else
