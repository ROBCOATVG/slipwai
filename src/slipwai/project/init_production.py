"""`./init`'s path to production: the shell fragments a managed target adds to the bootstrap script.

`init_script.py` assembles the script and decides whether these appear at all (`managed(CATALOG, target)`);
what each fragment says about the cloud and its tools is formatted in there too, from the same tables
`preflight` refuses on. Nothing here runs during generation — these are sources for the generated `./init`.
"""
from __future__ import annotations

# `./init` is run more than once: to answer an axis again, to add an extension, to switch or add a harness.
# Every one of those is local, and none of them should need administrator credentials to end green — which
# is what every rerun on a deployed project did need before reruns were fixed, because nothing asked whether
# the account had already been bootstrapped, and an expired cloud session then failed a run whose real work
# was done.
# The committed bootstrap state is the evidence: `make bootstrap` writes `infra/bootstrap/terraform.tfstate`
# (encrypted, and committed with the outputs it wrote), so where it exists the bootstrap has run and
# `make bootstrap` is the way to run it again — after `add-service`, or when the stack changes — with the
# passphrase only its owner has. Decided before the tools check, so a rerun on a machine without `tofu` is
# not told what it would need for a step it is not going to take. `--skip-bootstrap` said so already and is
# left alone, and the closing message at the end of `./init` says what was found and what re-applies.
ALREADY_BOOTSTRAPPED = """
bootstrapped=false
if [ "$skip_bootstrap" != true ] && [ -f infra/bootstrap/terraform.tfstate ]; then
  bootstrapped=true
  skip_bootstrap=true
fi
"""

# What the bootstrap will need, put there first — before Spec Kit is installed or anything else is done.
# The target's own setup hook runs where it has one (`SETUP`, a script the package ships): it knows its
# tools, where each comes from on this machine, and what it has to be told once, and `./init` knows none of
# that — it runs the hook and then looks, as it always did. `gh` is the keel's own need, every managed target
# pushing to a forge, so the keel installs it the same way and signs it in where there is a terminal.
# `--no-install` only looks. Not fatal either way: the rest of `./init` is local and still worth doing; only
# the push and bootstrap wait.
PRODUCTION_CHECK = """
if [ "$skip_bootstrap" != true ]; then
{setup}  if ! command -v gh >/dev/null 2>&1 && [ -z "${{GITEA_TOKEN:-}}" ] && [ "$no_install" != true ]; then
    if command -v brew >/dev/null 2>&1; then printf '%s\\n' 'Installing gh: brew install gh'; brew install gh || true
    elif command -v apt-get >/dev/null 2>&1; then printf '%s\\n' 'Installing gh: sudo apt-get install -y gh'; sudo apt-get install -y gh || true
    elif command -v dnf >/dev/null 2>&1; then printf '%s\\n' 'Installing gh: sudo dnf install -y gh'; sudo dnf install -y gh || true
    elif command -v winget >/dev/null 2>&1; then printf '%s\\n' 'Installing gh: winget install --id GitHub.cli -e'; winget install --id GitHub.cli -e || true
    fi
  fi
  if command -v gh >/dev/null 2>&1 && [ -z "${{GITEA_TOKEN:-}}" ] && ! gh auth status >/dev/null 2>&1; then
    if [ -r /dev/tty ] && [ "$no_install" != true ]; then
      printf '%s\\n' 'gh is not signed in; signing in now (Ctrl-C to do it later with `gh auth login`).'
      gh auth login </dev/tty || true
    else
      printf '%s\\n' 'gh is not signed in: run `gh auth login`, or set GITEA_TOKEN for Gitea.'
    fi
  fi
  missing=
  for tool in {tools}; do command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"; done
  if ! command -v gh >/dev/null 2>&1 && [ -z "${{GITEA_TOKEN:-}}" ]; then missing="$missing gh-or-GITEA_TOKEN"; fi
  if [ -n "$missing" ]; then
    printf '%s\\n' "This project deploys to {cloud}, and bootstrapping it needs:$missing (see 'Before ./init' in README.md)."
    printf '%s\\n\\n' 'Continuing without the push and bootstrap; when they are there: ./init --repository <url>, or push and run `make bootstrap`.'
    skip_bootstrap=true
  fi
fi
"""

# The path to production, made the last thing `./init` does — because the pipeline is configured on the forge
# and needs an account, so the first-day step has to know where the repository lives and be run by someone
# with the credentials. Asked once; skipped with `--skip-bootstrap`, or answered ahead with `--repository`;
# and not asked again once the committed state says it was done (`ALREADY_BOOTSTRAPPED`, above).
# Read from the terminal rather than stdin, so a scripted `./init` with no terminal skips rather than hangs;
# and never fatal to the rest of `./init`: Spec Kit and the agent projections are already in place by here.
#: The hook's line, for a target that ships one. Never fatal: what it could not do, the check below names.
SETUP_HOOK = """  if [ "$no_install" != true ] && [ -f {hook} ]; then
    python3 {hook} || printf '%s\\n' '{hook} did not finish; whatever it could not put here is named below.' >&2
  fi
"""


def setup_fragment(hook: str | None) -> str:
    """The hook's line, or nothing for a target without one."""
    return SETUP_HOOK.format(hook=hook) if hook else ""


PRODUCTION_BOOTSTRAP = """
if [ "$skip_bootstrap" != true ]; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    if [ -z "$repository" ] && [ -r /dev/tty ]; then
      printf '\\n%s\\n' 'This project deploys to {cloud}. The pipeline is configured on the repository it is pushed to.'
      printf '%s' 'Repository to push to (a URL on GitHub or Gitea, created if missing; Enter to do this later): '
      read -r repository </dev/tty || repository=
    fi
    if [ -n "$repository" ]; then
      # Not fatal under `set -e`: a push that fails has already said why, and letting it end `./init` here
      # would swallow the line below that says how to pick this up again.
      python3 scripts/bootstrap.py push "$repository" || true
    fi
  fi
  if git remote get-url origin >/dev/null 2>&1; then
    if ! make bootstrap ${{auto_promote:+AUTO_PROMOTE="$auto_promote"}}; then
      printf '%s\\n' 'The bootstrap did not finish; fix what it reported and run `make bootstrap` again.' >&2
      exit 1
    fi
  else
    printf '%s\\n' 'Not bootstrapped. When the repository exists: ./init --repository <url>, or push and run `make bootstrap`.'
  fi
elif [ "$bootstrapped" = true ]; then
  printf '%s\\n' 'Already bootstrapped: infra/bootstrap/terraform.tfstate is committed, so the account was left alone. `make bootstrap` re-applies the stack after add-service or a change under infra/bootstrap/.'
fi
"""
