"""`./init`'s path to production: the shell fragments a managed target adds to the bootstrap script.

`init_script.py` assembles the script and decides whether these appear at all (`managed(CATALOG, target)`);
what each fragment says about the cloud and its tools is formatted in there too, from the same tables
`preflight` refuses on. Nothing here runs during generation — these are sources for the generated `./init`.
"""
from __future__ import annotations

# `./init` is run more than once: to answer an axis again, to add an extension, to switch or add a harness.
# Every one of those is local, and none of them should need administrator credentials to end green — which
# is what every rerun on an AWS project did need before reruns were fixed, because nothing asked whether the account
# had already been bootstrapped, and an expired `aws` session then failed a run whose real work was done.
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

# What the bootstrap will need, checked first — before Spec Kit is installed or anything else is done — so
# the first thing `./init` says is what is missing, in the order the README's "Before `./init`" lists it.
# Not fatal: the rest of `./init` is local and still worth doing; only the push and bootstrap wait.
PRODUCTION_CHECK = """
if [ "$skip_bootstrap" != true ]; then
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
