#!/usr/bin/env zsh
# Run as the `mac` user in a zsh login shell (so ~/.zprofile's `brew shellenv` applies), the way Terminal.app
# opens one. slipwai is told it is on macOS (SLIPWAI_HOST_SYSTEM=macos, set in the image).
FAILED=0
pass() { print "PASS: $*" }
fail() { print "FAIL: $*"; FAILED=1 }
print -- "--- the machine"
print "login shell: $SHELL (zsh $ZSH_VERSION); /bin/sh: $(sh --version | head -1)"
print "make: $(make --version | head -1); python3: $(python3 --version 2>&1); brew: $(brew --version | head -1)"
sudo sh -c 'printf "#!/bin/sh\necho claude-stub\n" > /usr/local/bin/claude; chmod +x /usr/local/bin/claude'  # Spec Kit checks for it
cp ~/.zprofile /tmp/zprofile.before

print -- "\n--- install slipwai the documented way: uv, then uv tool install"
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
source ~/.local/bin/env 2>/dev/null
uv tool install /wheel/slipwai-*.whl >/dev/null 2>&1 && pass "uv tool install slipwai ($(slipwai --version))" || fail "could not install slipwai"

print -- "\n--- slipwai generate: TypeScript + React, installing what is missing"
mkdir -p ~/work && cd ~/work
out=$(slipwai generate myapp --install --init --integration claude --output ~/work </dev/null 2>&1); code=$?
print -- "$out" | grep -E "install-tools:|Could not|Running ./init|is done|exited|Not running" | head -20
[[ $code -eq 0 ]] && pass "generate exits 0" || fail "generate exited $code"
hash -r
[[ "$(python3 -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null)" == True ]] \
  && pass "python3 is new enough now: $(python3 --version) at $(command -v python3)" || fail "python3 still too old: $(python3 --version 2>&1)"
command -v node >/dev/null && pass "node: $(node --version) at $(command -v node)" || fail "no node"
case "$out" in *"brew install"*) pass "installs went through Homebrew" ;; *) fail "no Homebrew install ran" ;; esac
case "$out" in *"is done"*) pass "./init (under bash 3.2 as /bin/sh) ran to the end" ;; *) fail "./init did not finish" ;; esac
P=~/work/myapp
n=$(ls $P/.claude/commands 2>/dev/null | wc -l | tr -d ' '); (( n > 10 )) && pass "Claude commands projected ($n)" || fail "Claude commands missing ($n)"
python3 -c "import yaml" 2>/dev/null && pass "python3 imports yaml" || fail "python3 has no yaml"

print -- "\n--- Spec Kit's own bash script, under bash 3.2"
cd $P
spec=$(bash .specify/scripts/bash/create-new-feature.sh --json "try the preset composition" 2>&1)
print -- "$spec" | tail -2
case "$spec" in *'"SPEC_FILE"'*) pass "create-new-feature.sh works under bash 3.2" ;; *) fail "create-new-feature.sh failed under bash 3.2" ;; esac
git checkout -q -- . 2>/dev/null; git clean -qfd specs 2>/dev/null; git checkout -q main 2>/dev/null

print -- "\n--- the project's own gate, under GNU Make 3.81"
git add -A >/dev/null 2>&1 && git -c user.email=m@e.com -c user.name=m commit -qm "Install Spec Kit" >/dev/null 2>&1
ok=0
for try in 1 2 3; do
  timeout 900 make verify > /tmp/verify.log 2>&1 && { ok=1; break }
  grep -qE "ECONNRESET|ETIMEDOUT|network" /tmp/verify.log || break
  print "retrying after a network error ($try)"
done
(( ok )) && pass "make verify passes under make 3.81" || { fail "make verify failed under make 3.81"; tail -20 /tmp/verify.log }

print -- "\n--- the interactive way: an empty folder, \`slipwai generate\` in a real terminal, answered by hand"
mkdir -p ~/work/by-hand && cd ~/work/by-hand
python3 /t/drive-generate.py slipwai generate
[[ -f ~/work/by-hand/project.json ]] && pass "the empty folder became the project" || fail "project not written into the folder"
[[ ! -e ~/work/by-hand/by-hand ]] && pass "nothing nested beneath it" || fail "a folder was nested"
n=$(ls ~/work/by-hand/.claude/commands 2>/dev/null | wc -l | tr -d ' '); (( n > 10 )) && pass "Claude commands in the folder ($n)" || fail "no Claude commands ($n)"
cd ~

print -- "\n--- what it did to the login profile"
diff /tmp/zprofile.before ~/.zprofile >/dev/null && print "~/.zprofile unchanged" || { print "~/.zprofile changed:"; diff /tmp/zprofile.before ~/.zprofile }
(( FAILED )) && print "SOME FAILED" || print "ALL PASSED"
