"""The extension half of `./init`: the menu that offers them, and the shell that elects and runs them.

Split out of `init_script.py` when the guard offer arrived and that module reached its budget — which is
what the budget is for. The two halves are a real seam rather than a convenient one: everything here is
about *optional dev tooling a person chooses*, and what is left there is about the bootstrap every project
gets whether or not anybody chooses anything.

Two answers are taken here and they are deliberately separate. **Electing** an extension installs it and
runs its hooks, which are never fatal to a rung. **Agreeing** to its guards lets it refuse a tool call, so
`--offer` asks once, over `/dev/tty`, and silence is no.
"""
from __future__ import annotations

import json


def _sh_single_quote(text: str) -> str:
    """Embed prose as a literal single-quoted /bin/sh argument."""
    return "'" + text.replace("'", "'\"'\"'") + "'"


# A project generated from a quickstart was already told which extensions to elect, by somebody who
# answered that question when they wrote the quickstart. So the record is read before the menu below, and
# the menu then never appears: asking again would be asking a person to repeat themselves, which is the
# whole thing a quickstart exists to stop. `--extension` on the command line still wins, because both are
# gated on `selected_extensions` being empty and the flag is read first — an explicit answer is never
# second-guessed — and a project that came from no quickstart gets an empty line here and the menu as it was.
ELECTED_FROM_QUICKSTART = """
if [ -z "$selected_extensions" ] && command -v python3 >/dev/null 2>&1; then
  selected_extensions=$(python3 scripts/extensions/elected.py)
  if [ -n "$selected_extensions" ]; then
    printf '%s\\n' "Electing from this project's quickstart:$selected_extensions (./init --extension <key> adds another)"
  fi
fi
"""


# Not part of Spec Kit's own interactive flow: `specify init` prompts for `--integration` when it is
# omitted, but it knows nothing about this project's own `--extension` flags, so without this nothing ever
# asks. Offered only when no `--extension` was already given — an explicit answer, empty or not, is never
# second-guessed. `scripts/extensions/menu.py` is the checkbox menu itself (arrow keys move, Enter or
# Space checks, a Confirm row finishes) and owns the "is there actually a usable terminal" decision — it reads and writes
# `/dev/tty` directly rather than stdin/stdout, and prints nothing at all when that fails, so a scripted or
# CI `./init` gets silence and no extensions, exactly as if `--extension` had never been mentioned.
# Answering later is always available too — `./init --extension <key>` — so declining here costs nothing.
def prompt_extensions(catalog_extensions: dict) -> str:
    options = [
        {"key": key, "name": spec["name"], "description": spec["description"]}
        for key, spec in sorted(catalog_extensions.items())
    ]
    payload = _sh_single_quote(json.dumps(options))
    return f"""
if [ -z "$selected_extensions" ] && command -v python3 >/dev/null 2>&1; then
  selected_extensions=$(printf '%s' {payload} | python3 scripts/extensions/menu.py)
fi
"""


# The `init` point, fired through the registry like every other point — which is what slice 6.1e closed.
# Until then this loop ran a file called `init.py` by name, so an extension that declared a different script
# at that point was ignored: installed, valid, and silently never run, which is the convention-not-
# declaration failure `hooks.py` opens by describing. The registry is written first now, from
# `available.json`, and `hooks.py init` fires whatever each elected extension declared there — `init.py` by
# default, because that is the one file an extension is guaranteed to have (`hooks.DEFAULTS`).
#
# Never fatal to the rest of `./init`: Spec Kit and the agent projection are already in place by here, and
# `hooks.py` exits 0 whatever a hook did, reporting a failure as a `hook` line naming the extension and the
# last thing it printed. A key nothing shipped is one of those lines rather than a stopped bootstrap.
# `SLIPWAI_INTEGRATION` carries the harness chosen on this run to a hook that adds to `skills/` and has to
# re-project it: Spec Kit records the integration for later runs, but a hook running inside the same
# `./init` cannot rely on that record being there yet.
#
# Before the agent projection, the extensions already adopted here are re-projected: one that names its MCP
# server in each installed harness's project file has another file to write when a harness is added later
# (`./init --integration <agent>` on a project that adopted it earlier), and Spec Kit has recorded the new
# harness by this point. As non-fatal as everything below.
#
# Then one more projection pass, because that order has a cost: an extension points the agent at itself by
# appending to `AGENTS.md`, and a harness whose `contextMode` is `copy` reads a file Spec Kit wrote from
# `AGENTS.md` before any of this ran. Without the pass its copy never gains the pointer, and the extension
# is installed but never queried. `--context` carries only the marker-fenced regions across — and writes the
# `@AGENTS.md` include an `import` harness reads the whole file through — as non-fatal as the hooks above.
RUN_EXTENSIONS = """
if [ -n "$selected_extensions" ]; then
  python3 scripts/extensions/hooks.py --elect $selected_extensions || printf '%s\n' 'The hook registry was not written; `python3 scripts/extensions/hooks.py --elect <keys>` writes it.' >&2
  SLIPWAI_INTEGRATION="$selected_integration" python3 scripts/extensions/hooks.py init || printf '%s\n' 'Extension setup did not finish; `python3 scripts/extensions/hooks.py init` retries it.' >&2
  python3 scripts/extensions/guards.py --offer $selected_extensions || printf '%s\n' 'The guard registry was not written; nothing may refuse a tool call until `python3 scripts/extensions/guards.py --elect <keys>` says so.' >&2
  if [ -n "$selected_integration" ]; then
    python3 scripts/agents/project.py --context "$selected_integration" || printf '%s\n' 'The extension pointers did not reach the agent context file; `make agents` retries it.' >&2
  else
    python3 scripts/agents/project.py --context || printf '%s\n' 'The extension pointers did not reach the agent context file; `make agents` retries it.' >&2
  fi
fi
"""


# Spec Kit's own scripts compose this project's preset templates with PyYAML from 1.0.9 on: a
# `.specify/scripts/bash/create-new-feature.sh` that finds `preset.yml` and no `yaml` module on the `python3`
# it calls stops with "PyYAML is required to resolve preset template composition" — at the first
# `/speckit-specify`, hours after `./init` ran, with no remedy given. So it is checked here, against the
# `python3` those scripts call, only where the installed Spec Kit mentions it, and put right where it can be.
# The user site is tried first, and fails on purpose under PEP 668 (Homebrew's and Debian's Python refuse
# pip outside a venv); then a venv under `.delivery-tools/` that sees the system's packages, which the person
# puts first on PATH — `python3` is what the scripts call, so nothing here can be pointed at it any other way.
# Never fatal: Spec Kit is installed by now, and this is a message with the fix in it rather than a failed
# bootstrap. `.delivery-tools/` is already gitignored for the event-model check's own `--target` installs.
