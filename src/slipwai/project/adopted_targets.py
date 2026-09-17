"""The Make targets an adopted repository has and a generated project does not, appended to the delivery Makefile.

Brownfield adoption (experimental as `AGENTS.md` defines the word). Three of them: `check-convergence` and
`ratchet-tighten`, the map's gate and the ratchet's re-recording; `smoke`, each application that existed before
the method did started by the command it recorded and proved to answer — the one thing the day-one gate cannot
compose from the eight recorded commands, run by `ci` and by a job of its own in the gate's workflow and never by
`verify`, since it needs what the application needs; and `test-full` where a suite too slow for `verify` was
recorded. Split from `adopted.py` when the smoke target took the pages and the targets together past the module
budget, the way `adopted_ci.py` was.
"""
from __future__ import annotations

from ..layout import Layout
from ..services import App, wrapped_of


def smoke_lines(wrapped: list[App], layout: Layout) -> str:
    """One recipe line per wrapped application: its recorded `smoke` command as it stands; a `null` said and passed,
    since it is a written no with its reason in `survey/running.md`; and, where no key was ever written, a line that
    says the application has not been proved to start — which is the programme's step after the build, and what
    `/ground` asks for — rather than a guess at how it might."""
    running = layout.under("survey/running.md")
    lines = []
    for app in wrapped:
        commands = app.commands or {}
        command = commands.get("smoke")
        if command:
            lines.append(f"\t{command.replace('$', '$$')}\n")
        elif "smoke" in commands:
            lines.append(f"\t@echo '{app.name}: smoke is recorded as a written no in project.json; {running} says why'\n")
        else:
            lines.append(
                f"\t@echo '{app.name}: no smoke command is recorded — nobody has proved how it starts ({running}). "
                "/ground asks for the command that starts it and proves it answers, recorded as commands.smoke'\n"
            )
    return "".join(lines)


def adoption_targets(apps: list[App], layout: Layout) -> str:
    """For a project with applications that existed before the method did: the ratchet's re-recording, each
    application started by its recorded `smoke` command and proved to answer, and the full suites they recorded as
    too slow for `verify`. Nothing for a generated project."""
    wrapped = wrapped_of(apps)
    if not wrapped:
        return ""
    full = [(app, (app.commands or {}).get("test-full")) for app in wrapped]
    full_lines = "".join(f"\t{command.replace('$', '$$')}\n" for _, command in full if command)
    test_full = f"""
.PHONY: test-full
test-full: ## Run the full suites recorded as too slow for verify (test is the fast subset)
{full_lines}""" if full_lines else ""
    return f"""
.PHONY: check-convergence
check-convergence: ## Fail when the convergence map claims a rung the tree contradicts, or docs/convergence.md is stale
\tpython3 scripts/check-convergence.py

.PHONY: ratchet-tighten
ratchet-tighten: ## Re-record the lint, typecheck and test baselines from the current findings, after looking at them
\tRATCHET_TIGHTEN=1 $(MAKE){layout.make_flag} --no-print-directory lint typecheck test

.PHONY: smoke
smoke: ## Start each application by its recorded smoke command and prove it answers (ci runs it; verify does not)
{smoke_lines(wrapped, layout)}{test_full}"""
