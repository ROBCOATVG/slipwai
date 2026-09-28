"""`./init`'s PyYAML step: the one module Spec Kit's own scripts need that a bare `python3` may not have.

`init_script.py` assembles the script and places this after Spec Kit is installed; nothing here runs during
generation — this is a source for the generated `./init`.
"""
from __future__ import annotations

from ..host import uv_by_uname

# Spec Kit's own scripts compose this project's preset templates with PyYAML from 1.0.9 on: a
# `.specify/scripts/bash/create-new-feature.sh` that finds `preset.yml` and no `yaml` module on the `python3`
# it calls stops with "PyYAML is required to resolve preset template composition" — at the first
# `/speckit-specify`, hours after `./init` ran, with no remedy given. So it is checked here, against the
# `python3` those scripts call, only where the installed Spec Kit mentions it, and put right.
#
# Those scripts take `python3` off the PATH and nothing else, so PyYAML has to be importable by *that*
# interpreter with no step of the person's. An earlier answer built a venv under `.delivery-tools/` and asked
# for it to be put first on PATH before starting the agent — a step every shell had to remember, and one no
# agent session inherits. The place that needs no step is where `python3` already looks: its venv, if it is a
# venv's, and otherwise its user site, which it puts on `sys.path` by itself.
#
# uv does the installing, because uv is what slipwai is installed with: `uv pip install --python python3`
# targets that interpreter without needing its pip, and `--target` writes into the user site as a directory
# rather than into the managed environment, so a PEP 668 Python (Homebrew's, Debian's) has nothing to refuse
# and the system's packages are never touched. A machine without uv — a clone on a teammate's laptop — is told
# the line that installs uv there. A Python with its user site switched off is not second-guessed.
# Never fatal: Spec Kit is installed by now, and this is a message with the fix in it rather than a failed
# bootstrap.
PYYAML_FOR_SPECKIT = """
if grep -qs 'PyYAML' .specify/scripts/bash/*.sh && ! python3 -c 'import yaml' >/dev/null 2>&1; then
  yaml_home=$(python3 -c 'import site, sys; print("venv" if sys.prefix != sys.base_prefix else (site.getusersitepackages() if site.ENABLE_USER_SITE else ""))' 2>/dev/null || true)
  if command -v uv >/dev/null 2>&1 && [ -n "$yaml_home" ]; then
    if [ "$yaml_home" = venv ]; then
      uv pip install --quiet --python python3 PyYAML >/dev/null 2>&1 || true
    else
      uv pip install --quiet --python python3 --target "$yaml_home" PyYAML >/dev/null 2>&1 || true
    fi
  fi
  if python3 -c 'import yaml' >/dev/null 2>&1; then
    printf '%s\\n' "Installed PyYAML for python3: Spec Kit's scripts compose this project's preset templates with it."
  else
    cat >&2 <<'EOF'
Spec Kit's scripts need PyYAML on python3 to compose this project's preset templates, and it could not be
installed for the python3 on PATH here. With uv on PATH, rerun ./init and it will be; or install it for that
python3 yourself (your package manager's python3-yaml). Without it,
.specify/scripts/bash/create-new-feature.sh stops with "PyYAML is required".
EOF
    if ! command -v uv >/dev/null 2>&1; then
""" + uv_by_uname() + """    fi
  fi
fi
"""
