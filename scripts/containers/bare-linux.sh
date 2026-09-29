#!/bin/sh
# A bare Debian with Python and nothing else: does one slipwai command leave a working project, installing
# everything itself? MODE=generate or MODE=adopt. /src is the branch, read-only.
set -u
FAILED=0
pass() { printf 'PASS: %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; FAILED=1; }
apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends python3 ca-certificates >/dev/null
printf '#!/bin/sh\necho claude-stub\n' > /usr/local/bin/claude; chmod +x /usr/local/bin/claude   # Spec Kit checks for it
for t in git node npm npx uv make; do command -v $t >/dev/null && echo "pre-existing: $t"; done
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/src/src
SW="python3 -m slipwai"

if [ "$MODE" = generate ]; then
  cd /tmp && out=$($SW generate app --install --init --integration claude --output /tmp/g </dev/null 2>&1); code=$?
  P=/tmp/g/app
else
  # The one thing a repository to adopt has: git, since it is a Git repository.
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends git >/dev/null
  git config --global user.email p@e.com; git config --global user.name p; git config --global init.defaultBranch main
  mkdir -p /tmp/shop && cd /tmp/shop && git init -q && printf '{"name":"shop","scripts":{"test":"node -e 0"}}\n' > package.json
  git add -A && git commit -qm init
  out=$($SW adopt --yes --install --init --integration claude </dev/null 2>&1); code=$?
  P=/tmp/shop
fi
echo "$out" | grep -E "install-tools|Running ./|is done|Could not install|Not running|exited" | head -20
[ $code -eq 0 ] && pass "$MODE exits 0" || fail "$MODE exited $code"
export PATH="$HOME/.local/bin:$PATH"
for t in git node npm make uv; do command -v $t >/dev/null && pass "$t installed ($($t --version 2>&1 | head -1))" || fail "$t not installed"; done
case "$out" in *"is done"*) pass "./init ran to the end" ;; *) fail "./init did not finish" ;; esac
case "$out" in *"uv installs with"*|*"Install it:"*|*"curl -"*) fail "a hand-run install line was printed" ;; *) pass "no install line handed to the person" ;; esac
n=$(ls $P/.claude/commands 2>/dev/null | wc -l); [ "$n" -gt 10 ] && pass "Claude commands projected ($n)" || fail "Claude commands missing ($n)"
python3 -c "import yaml" 2>/dev/null && pass "python3 imports yaml (PyYAML for Spec Kit)" || fail "no PyYAML"

cd $P && D=$([ "$MODE" = adopt ] && echo delivery/ || echo "")
ext=$(./${D}init --extension codegraph 2>&1); echo "$ext" | tail -4
[ -d .codegraph ] && pass "CodeGraph indexed this project" || fail "no .codegraph index"
[ ! -e "$HOME/.claude.json" ] && [ ! -e "$HOME/.claude/CLAUDE.md" ] && pass "CodeGraph left global agent config alone" || fail "CodeGraph wrote global agent config"
case "$ext" in *"Install it"*|*"curl -"*) fail "CodeGraph asked for a hand install" ;; *) pass "CodeGraph needed nothing run by hand" ;; esac

if [ "$MODE" = generate ]; then
  git add -A >/dev/null 2>&1 && git -c user.email=p@e.com -c user.name=p commit -qm "Install Spec Kit" >/dev/null 2>&1
  ok=0; for try in 1 2 3; do timeout 900 make verify > /tmp/verify.log 2>&1 && { ok=1; break; }; grep -q "ECONNRESET\\|ETIMEDOUT\\|network" /tmp/verify.log || break; echo "retrying after a network error ($try)"; done
  [ $ok = 1 ] && pass "the new project's make verify passes" || { fail "make verify failed"; tail -15 /tmp/verify.log; }
fi
[ $FAILED -eq 0 ] && echo "ALL PASSED" || echo "SOME FAILED"
