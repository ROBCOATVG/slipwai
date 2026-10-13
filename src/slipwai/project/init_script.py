"""`./init`: the bootstrap that installs Spec Kit and prunes what the project was not given.

Spec Kit is deliberately absent from a generated repository until this script is run, and the axis flags it
takes are the project's own rather than Spec Kit's, so they are lifted out before the rest is forwarded.
Once it has run, a rerun that forwards nothing — `./init --extension <key>`, a re-answered axis,
`./init --repository <url>` — leaves Spec Kit alone: everything such a rerun does is local or forge-bound,
and reinstalling Spec Kit is the one step that needs to reach its source, so repeating it made every rerun
fail wherever that host is unreachable.
"""
from __future__ import annotations

from ..catalog import CATALOG, axis_prunable
from ..extensions import known_extensions
from ..layout import AT_ROOT, Layout
from ..loaded_targets import cloud_of, setup_for, tools_for
from ..services import App, axes_of, services_of
from ..targets import managed
from .init_extensions import ELECTED_FROM_QUICKSTART, RUN_EXTENSIONS, prompt_extensions
from .init_languages import LANGUAGES_CHECK
from .init_production import ALREADY_BOOTSTRAPPED, PRODUCTION_BOOTSTRAP, PRODUCTION_CHECK, setup_fragment
from .pins import SPECKIT_SOURCE


# The axis and extension flags are this project's own, not Spec Kit's, so they are lifted out of the
# argument list before the rest is forwarded to `specify`. The rotate-and-reappend idiom rebuilds "$@"
# without an array, which /bin/sh does not have. An axis flag's value is a single bare token (postgres,
# memory, fastify, keycloak, none), which is what makes the unquoted $backing_flags expansion below safe.
#
# Generated from the axes the project can still answer, the extensions the catalog knows about, and
# whether this project has a production target, rather than written out, so a flag that would only ever be
# refused is never advertised: an axis settled at generation time drops out here, and a catalog with no
# extensions yet emits no `--extension` handling at all — including no `selected_extensions` variable,
# which is why the dispatch loop below is gated on the same condition.
#
# `--extension` is repeatable, unlike `--integration`: a project can adopt more than one dev-tool hook in
# one `./init`, so each occurrence appends to `selected_extensions` rather than overwriting it.
def argument_scan(axes: list[str], extensions: list[str], production: bool = False) -> str:
    axis_joined = "|".join(f"--{axis}" for axis in axes)
    axis_inline = "".join(
        f'    --{axis}=*) backing_flags="$backing_flags --{axis} ${{argument#--{axis}=}}" ;;\n'
        for axis in axes
    )
    axis_variables = "expect_backing=\nbacking_flags=\n" if axes else ""
    axis_expect = (
        """  if [ -n "$expect_backing" ]; then
    backing_flags="$backing_flags $expect_backing $argument"
    expect_backing=
    continue
  fi
"""
        if axes
        else ""
    )
    axis_case = f"    {axis_joined}) expect_backing=$argument ;;\n{axis_inline}" if axes else ""
    axis_error = (
        """if [ -n "$expect_backing" ]; then
  printf '%s\n' "$expect_backing needs a value; scripts/backing-services.py --list shows them." >&2
  exit 2
fi
"""
        if axes
        else ""
    )
    extension_variables = "expect_extension=false\nselected_extensions=\n" if extensions else ""
    extension_expect = (
        """  if [ "$expect_extension" = true ]; then
    selected_extensions="$selected_extensions $argument"
    expect_extension=false
    continue
  fi
"""
        if extensions
        else ""
    )
    extension_case = (
        """    --extension) expect_extension=true ;;
    --extension=*) selected_extensions="$selected_extensions ${argument#--extension=}" ;;
"""
        if extensions
        else ""
    )
    # The production target's own flags: where to push, and whether to bootstrap at all. Lifted out like
    # the axis and extension flags, because Spec Kit would refuse them.
    production_variables = (
        "repository=\nexpect_repository=false\nskip_bootstrap=false\nno_install=false\nauto_promote=\n"
        "expect_auto_promote=false\n"
        if production
        else ""
    )
    production_expect = (
        """  if [ "$expect_repository" = true ]; then
    repository=$argument
    expect_repository=false
    continue
  fi
  if [ "$expect_auto_promote" = true ]; then
    auto_promote=$argument
    expect_auto_promote=false
    continue
  fi
"""
        if production
        else ""
    )
    production_case = (
        """    --repository) expect_repository=true ;;
    --repository=*) repository=${argument#--repository=} ;;
    --auto-promote) expect_auto_promote=true ;;
    --auto-promote=*) auto_promote=${argument#--auto-promote=} ;;
    --skip-bootstrap) skip_bootstrap=true ;;
    --no-install) no_install=true ;;
"""
        if production
        else ""
    )
    return f"""
selected_integration=
expect_integration=false
{axis_variables}{extension_variables}{production_variables}remaining=$#
while [ "$remaining" -gt 0 ]; do
  argument=$1
  shift
  remaining=$((remaining - 1))
{axis_expect}{extension_expect}{production_expect}  if [ "$expect_integration" = true ]; then
    selected_integration=$argument
    expect_integration=false
    set -- "$@" "$argument"
    continue
  fi
  case "$argument" in
    --integration) expect_integration=true; set -- "$@" "$argument" ;;
    --integration=*) selected_integration=${{argument#--integration=}}; set -- "$@" "$argument" ;;
{axis_case}{extension_case}{production_case}    *) set -- "$@" "$argument" ;;
  esac
done
{axis_error}"""


# Pruning runs before `run_specify`: it is local and instant, so an unusable selection fails before any
# network work rather than leaving a half-initialised project behind.
PRUNE_BACKING_SERVICES = """
if [ -n "$backing_flags" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3 is required to prune the local backing services.' >&2
    exit 1
  fi
  python3 scripts/backing-services.py $backing_flags
else
  printf '%s\n' 'Backing services left as generated; scripts/backing-services.py --list shows what can still be changed.'
fi
"""

PYYAML_FOR_SPECKIT = """
if grep -qs 'PyYAML' .specify/scripts/bash/*.sh && ! python3 -c 'import yaml' >/dev/null 2>&1; then
  if python3 -m pip install --disable-pip-version-check --quiet --user PyYAML >/dev/null 2>&1 \\
     && python3 -c 'import yaml' >/dev/null 2>&1; then
    printf '%s\\n' "Installed PyYAML for python3: Spec Kit's scripts compose this project's preset templates with it."
  elif python3 -m venv --system-site-packages .delivery-tools/venv >/dev/null 2>&1 \\
     && .delivery-tools/venv/bin/python -m pip install --disable-pip-version-check --quiet PyYAML >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Spec Kit's scripts need PyYAML on python3 to compose this project's preset templates, and this python3 will
not take it from pip (PEP 668: an externally managed environment). A venv with it is at .delivery-tools/venv,
sharing the system's packages; start the agent from a shell where that venv comes first:
    export PATH="$PWD/.delivery-tools/venv/bin:$PATH"
Without it, .specify/scripts/bash/create-new-feature.sh stops with "PyYAML is required".
EOF
  else
    cat >&2 <<'EOF'
Spec Kit's scripts need PyYAML on python3 to compose this project's preset templates, and neither pip nor a
venv could install it here. Install it for the python3 on PATH — `python3 -m pip install --user PyYAML`, or
your package manager's python3-yaml — and rerun ./init. Without it,
.specify/scripts/bash/create-new-feature.sh stops with "PyYAML is required".
EOF
  fi
fi
"""


def init_script(apps: list[App], target: str = "none", layout: Layout = AT_ROOT) -> str:
    # Every axis some service answered with something a later prune could take away. The rung is not one
    # of them: `--write-model state` would not remove an adapter, it would declare the history already on
    # disk to be no longer the truth, which is a migration somebody writes rather than a flag.
    prunable = [
        axis
        for axis in axes_of(apps)
        if axis_prunable(axis)
        and any(s.selection.option(axis) != CATALOG["axes"][axis]["absent"] for s in services_of(apps))
    ]
    production = managed(CATALOG, target)
    extensions = sorted(known_extensions(CATALOG))
    scan = argument_scan(prunable, extensions, production)
    prune = PRUNE_BACKING_SERVICES if prunable else ""
    # The tool list and the cloud's name are the target's own answers, so a second cloud changes the words
    # `./init` prints and nothing about what it does. They must be the same list `preflight` refuses on,
    # which is why both read the target's `tools` rather than a list of their own.
    cloud = cloud_of(target)
    check = (
        ALREADY_BOOTSTRAPPED + PRODUCTION_CHECK.format(tools=" ".join(tools_for(target)), cloud=cloud,
                                                       setup=setup_fragment(setup_for(target)))
        if production
        else ""
    )
    prompt = (ELECTED_FROM_QUICKSTART + prompt_extensions(known_extensions(CATALOG))) if extensions else ""
    run_extensions = RUN_EXTENSIONS if extensions else ""
    bootstrap = PRODUCTION_BOOTSTRAP.format(cloud=cloud) if production else ""
    # Spec Kit writes to the working directory, so this runs from the repository root wherever it was
    # invoked from — a step only a script that does not live at the root needs.
    to_root = (
        f'# This lives under {layout.delivery}/; everything below happens at the repository root.\n'
        f'cd "$(dirname "$0")/{layout.to_root}"\n' if layout.moved else ""
    )
    script = """#!/bin/sh
set -eu
""" + to_root + scan + check + LANGUAGES_CHECK + prompt + """
run_specify() {
  # The release this project records (`project.json`, `speckitSource`), so a rerun that restores the ignored
  # projections reinstalls the same Spec Kit rather than moving to upstream HEAD. SPECIFY_SOURCE overrides it.
  recorded=$(sed -n 's/.*"speckitSource": *"\\([^"]*\\)".*/\\1/p' project.json 2>/dev/null | head -n 1)
  source=${SPECIFY_SOURCE:-${recorded:-__SPECKIT_SOURCE__}}
  if command -v specify >/dev/null 2>&1; then
    specify init --here --force "$@"
    return
  fi

  if command -v uvx >/dev/null 2>&1; then
    uvx --from "$source" specify init --here --force "$@"
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv tool run --from "$source" specify init --here --force "$@"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    tools_dir=.specify-tools
    if [ ! -x "$tools_dir/bin/specify" ]; then
      package=${SPECIFY_PACKAGE:-$source}
      python3 -m pip install --disable-pip-version-check --upgrade --target "$tools_dir" "$package"
    fi
    PYTHONPATH="$tools_dir${PYTHONPATH:+:$PYTHONPATH}" "$tools_dir/bin/specify" init --here --force "$@"
    return
  fi

  cat >&2 <<'EOF'
Spec Kit is not installed, and neither uv nor Python 3 is available to install it.
Install uv or Python 3, then rerun ./init, or install the official specify CLI.
See https://github.com/github/spec-kit/blob/main/docs/installation.md
EOF
  return 1
}
""" + prune + """
# What "$@" still holds after the scan is exactly what Spec Kit is for; every flag this project answers
# itself was lifted out above. So an empty "$@" where `specify init` has already recorded an integration
# (`.specify/integration.json` — generation ships other files under `.specify/`, only Spec Kit writes this
# one) is a rerun asking nothing of Spec Kit: an extension add, a re-answered axis, a deferred push. All of
# that is local or forge-bound, while reinstalling Spec Kit needs its source host, so skipping it here is
# what lets such a rerun finish where that host is unreachable.
if [ $# -eq 0 ] && [ -f .specify/integration.json ]; then
  printf '%s\n' 'Spec Kit is already installed and nothing new was asked of it, so it was left alone; `./init --integration <agent>` reruns `specify init`.'
else
  run_specify "$@"
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Spec Kit initialized, but Python 3 is required to install the project skills and commands for the selected agent.' >&2
  exit 1
fi
""" + PYYAML_FOR_SPECKIT + """
if [ -f .slipwai/extensions.json ]; then
  python3 scripts/extensions/project.py || printf '%s\n' 'The adopted extensions were not re-projected; `make agents` retries it.' >&2
fi
if [ -n "$selected_integration" ]; then
  python3 scripts/agents/project.py "$selected_integration"
else
  python3 scripts/agents/project.py
fi
""" + run_extensions + bootstrap
    return script.replace("__SPECKIT_SOURCE__", SPECKIT_SOURCE)
