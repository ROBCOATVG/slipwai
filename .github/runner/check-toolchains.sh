#!/usr/bin/env bash
# Hold the job image to the toolchain versions this repository expects.
#
# This runs from the *checkout*, not from the image, and that is the whole point: an image that checked
# itself would agree with itself. Read against versions.env — the same file the image was built from — a
# rebuild that never happened, a runner still pointing at last month's tag, or a hand-edited pin all show up
# here, in the first job, naming the tool and both versions. That is the job `.github/actions/toolchains`
# does now that nothing installs a toolchain any more.
#
# Every mismatch is reported, not just the first: a stale image is usually stale in several places at once,
# and one rebuild should be able to fix all of them.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=versions.env
set -a; . "$here/versions.env"; set +a

failures=()

# `expect <tool> <expected> <actual>` — actual may carry a build suffix the publisher adds (pack prints
# `0.40.9+git-...`), so the expected version has to match at the front rather than exactly.
expect() {
  local tool=$1 expected=$2 actual=$3
  if [ -z "$actual" ]; then
    printf '  %-8s MISSING (expected %s)\n' "$tool" "$expected"
    failures+=("$tool: not on PATH, expected $expected")
  elif [ "$actual" = "$expected" ] || [ "${actual#"$expected"}" != "$actual" ]; then
    printf '  %-8s %s\n' "$tool" "$actual"
  else
    printf '  %-8s %s  != expected %s\n' "$tool" "$actual" "$expected"
    failures+=("$tool: image has $actual, versions.env expects $expected")
  fi
}

# Each of these is "" when the tool is absent, which `expect` reports rather than letting `set -e` kill the
# script on the first missing one.
version_of() { command -v "$1" >/dev/null 2>&1 && shift && "$@" 2>&1 || true; }

python_actual=$(version_of python3 python3 --version | awk '{print $2}')
node_actual=$(version_of node node --version | tr -d 'v')
go_actual=$(version_of go go version | awk '{print $3}' | sed 's/^go//')
# `java -version` writes to stderr and quotes the version: openjdk version "25.0.4.1" 2026-10-21
java_actual=$(version_of java java -version | awk -F'"' '/version/ {print $2; exit}')
tofu_actual=$(version_of tofu tofu version | awk 'NR==1 {print $2}' | tr -d 'v')
ko_actual=$(version_of ko ko version | tr -d 'v' | tr -d '[:space:]')
pack_actual=$(version_of pack pack --version | tr -d '[:space:]')

echo "toolchains provided by the job image:"
expect python3 "$PYTHON_VERSION" "$python_actual"
expect node "$NODE_VERSION" "$node_actual"
expect go "$GO_VERSION" "$go_actual"
expect java "$JAVA_VERSION" "$java_actual"
expect tofu "$TOFU_VERSION" "$tofu_actual"
expect ko "$KO_VERSION" "$ko_actual"
expect pack "$PACK_VERSION" "$pack_actual"

# Not pinned — these come from the base image, and a job only needs them to exist. The docker CLI matters
# most: every image test talks to the host daemon through the socket act_runner mounts.
echo "from the base image:"
for tool in docker git make npm; do
  printf '  %-8s %s\n' "$tool" "$(command -v "$tool" >/dev/null 2>&1 && "$tool" --version 2>&1 | head -1 || echo MISSING)"
done

if [ ${#failures[@]} -gt 0 ]; then
  cat >&2 <<MESSAGE

This job's image does not provide what .github/runner/versions.env pins:
$(printf '  - %s\n' "${failures[@]}")

Nothing installs toolchains in CI any more — they are baked into the image the runners are configured to
use, so this is a stale image or a pin that was bumped without one. Rebuild and roll it out:

  .github/runner/build.sh slipwai-ci:\$(date +%F)
  # then point the runners at the new tag — .github/runner/README.md
MESSAGE
  exit 1
fi

echo "all pinned toolchains match .github/runner/versions.env"
