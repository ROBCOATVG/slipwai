#!/usr/bin/env python3
"""Try it: the app at trunk's newest merge, running on this machine for a person to use.

`make demo` runs the checkout in containers and prints two addresses. Opening them on a voyage showed nothing
anyone could use: the slices' screens sat behind flags nothing turned on, the service in its container was
never told who may sign in, the database was empty, and an agent's leftover stack already held the ports.
Each of those is a reason a person stops trying. This is the one command that clears all of them, and the
board's Try it panel is a button on it.

**Its own workspace.** A detached worktree beside the checkout, `<root>-try`, at trunk's head. Never the
checkout itself: the harbourmaster merges there, and an app that reloads halfway through a merge shows a
person something no gate has passed. `refresh` moves the workspace to the newest merge.

**Its own ports and its own containers.** Every published port the Compose file names, and every app's port,
moved by `TRY_IT_PORT_OFFSET` (1000 unless set), under a Compose project of its own. A slice's stack and
this one can never take each other's ports or each other's data.

**The app on the host, the backing services in containers.** A browser and a service in a container reach a
sign-in server at two different addresses, and a service that checks a token's issuer against the address it
fetched its keys from refuses every token the browser was given. On the host there is one address.

**Settings built, never written.** `.env.example`, then `.env` where there is one, then the moved ports, then
every flag the code reads, `on` — handed to each process and never written to a file. Trying the app cannot
change what ships.

**The data the slices' examples describe.** Each slice that has a `try-it.json` beside its `quickstart.md`
is a story of API calls, made as the user it names. They go through the front door, so a record seeded here
is one the app would have accepted from a person.

State is `.slipwai/try-it/state.json`, which the board reads; the processes are detached and outlive both
the board and this command, the way the captains do.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
HOME = ROOT / ".slipwai/try-it"
STATE = HOME / "state.json"
#: Flags a person turned off on the panel. Kept apart from the state, which a fresh start rewrites.
FLAGS = HOME / "flags.json"
#: A published port in the Compose file: `'${KEYCLOAK_PORT:-8081}:8080'`.
PUBLISHED = re.compile(r"\$\{([A-Z][A-Z0-9_]*):-(\d+)\}:(\d+)")
#: How each browser framework's own reader is asked for a flag. The frameworks are the keel's own, so the
#: shape of their reader is too; a service's flags are declared, and read from where they are declared.
WEB_FLAG_CALLS = {"react-vite": re.compile(r"flagEnabled\(\s*['\"]([a-z0-9][a-z0-9-]*)['\"]")}
DECLARED_FLAGS = ROOT / "infra/service/flags.auto.tfvars"
DECLARED = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"", re.M)
#: A line of a `KEY=value` settings file.
SETTING = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
#: How long a process gets to answer before the start is said to have failed.
PATIENCE = 240


# ---- what the project is ------------------------------------------------------------------------------------

def manifest() -> dict:
    return json.loads((ROOT / "project.json").read_text(encoding="utf-8"))


def deployables() -> list[dict]:
    """Every app this project runs, in `project.json`'s order, with the Make target and port variable the
    generated Makefile gives it: the first of each kind is `dev`/`PORT` and `dev-web`/`WEB_PORT`, every other
    `dev-<name>`/`PORT_<NAME>`. A service with no transport has nothing to serve and is left out."""
    found: list[dict] = []
    seen = {"service": 0, "web": 0}
    for name, record in (manifest().get("deployables") or {}).items():
        kind = record.get("kind")
        if kind not in seen or not isinstance(record.get("port"), int):
            continue
        if kind == "service" and str((record.get("selection") or {}).get("http", "none")) == "none":
            continue
        first = seen[kind] == 0
        seen[kind] += 1
        suffix = "" if first else "_" + name.upper().replace("-", "_")
        found.append({"name": name, "kind": kind, "path": record.get("path", ""), "port": record["port"],
                      "api": record.get("api", ""),
                      "target": ("dev" if kind == "service" else "dev-web") if first else f"dev-{name}",
                      "variable": ("PORT" if kind == "service" else "WEB_PORT") + suffix})
    return found


def offset() -> int:
    try:
        return int(os.environ.get("TRY_IT_PORT_OFFSET", "1000"))
    except ValueError:
        return 1000


def walks() -> Path:
    """Where the demo hand's recordings go: under the main checkout, which the board reads, whichever
    worktree the hand walked from."""
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    main = Path(common).parent if common else ROOT
    return main / ".slipwai/walks"


def workspace() -> Path:
    return ROOT.parent / f"{ROOT.name}-try"


def git(*argv: str, where: Path = ROOT) -> str:
    done = subprocess.run(["git", "-C", str(where), *argv], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def trunk() -> str:
    """The branch merges land on: the local one first, because the harbourmaster merges here."""
    for candidate in ("main", "master", "origin/main", "origin/master"):
        if git("rev-parse", "--verify", "--quiet", candidate):
            return candidate
    return "HEAD"


def compose_ports(where: Path) -> dict[str, tuple[int, int]]:
    """Each port variable the Compose file publishes, with its default and the port Try it moves it to."""
    path = where / "docker-compose.yml"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {name: (int(default), int(default) + offset()) for name, default, _ in PUBLISHED.findall(text)}


def keycloak(where: Path) -> dict:
    """The sign-in server the Compose file runs, where it runs one: its port variable and its admin."""
    path = where / "docker-compose.yml"
    if not path.is_file():
        return {}
    block, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^  [a-z][a-z0-9-]*:\s*$", line):
            inside = line.strip() == "keycloak:"
            continue
        if inside:
            block.append(line)
    text = "\n".join(block)
    if "keycloak" not in text:
        return {}
    port = PUBLISHED.search(text)
    user = re.search(r"KC_BOOTSTRAP_ADMIN_USERNAME:\s*'?([^'\s]+)", text)
    word = re.search(r"KC_BOOTSTRAP_ADMIN_PASSWORD:\s*'?([^'\s]+)", text)
    return {"variable": port.group(1) if port else "", "user": user.group(1) if user else "admin",
            "password": word.group(1) if word else "admin"}


def realms(where: Path) -> list[dict]:
    folder = where / "docker/keycloak/realms"
    found = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            found.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return found


def people(where: Path) -> list[dict]:
    """Everyone a person can sign in as, from the local realms: a fixture, so its password is no secret."""
    found = []
    for realm in realms(where):
        for user in realm.get("users") or []:
            word = next((c.get("value") for c in user.get("credentials") or [] if c.get("type") == "password"), "")
            if not word or not user.get("enabled", True):
                continue
            name = " ".join(part for part in (user.get("firstName"), user.get("lastName")) if part)
            found.append({"name": name or user.get("username", ""), "username": user.get("username", ""),
                          "password": word, "realm": realm.get("realm", "")})
    return found


def flag_keys(where: Path) -> list[str]:
    """Every flag the code reads: the ones a target declares, and the ones each browser app asks for."""
    keys: set[str] = set()
    declared = where / DECLARED_FLAGS.relative_to(ROOT)
    if declared.is_file():
        keys |= {name.lower().removeprefix("flag_").replace("_", "-")
                 for name in DECLARED.findall(declared.read_text(encoding="utf-8"))}
    call = WEB_FLAG_CALLS.get(str(manifest().get("frontend", "")))
    for app in deployables():
        if app["kind"] != "web" or call is None:
            continue
        for path in (where / app["path"] / "src").rglob("*"):
            if path.is_file() and path.suffix in (".ts", ".tsx", ".js", ".jsx"):
                # Code, not the comments: the reader's own documentation names an example flag.
                code = "\n".join(line.split("//")[0] for line in path.read_text(encoding="utf-8", errors="replace")
                                 .splitlines() if not line.lstrip().startswith(("*", "/*")))
                keys |= set(call.findall(code))
    return sorted(keys)


def flag_states(where: Path) -> dict[str, str]:
    off = turned_off()
    return {key: "off" if key in off else "on" for key in flag_keys(where)}


def turned_off() -> set[str]:
    try:
        return set(json.loads(FLAGS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


# ---- the settings each process is handed --------------------------------------------------------------------

def settings_file(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        held = SETTING.match(line)
        if held and not line.lstrip().startswith("#"):
            found[held.group(1)] = held.group(2).strip().strip("'\"")
    return found


def environment(where: Path) -> dict[str, str]:
    """What every process Try it starts is handed: the project's settings with every port moved, the
    containers named for Try it, and the flags on."""
    moved = compose_ports(where)
    apps = {app["variable"]: (app["port"], app["port"] + offset()) for app in deployables()}
    ports = {**moved, **apps}
    told = {**settings_file(where / ".env.example"), **settings_file(ROOT / ".env")}
    for name, value in told.items():
        for old, new in ports.values():
            value = re.sub(rf"(localhost|127\.0\.0\.1):{old}\b", rf"\g<1>:{new}", value)
        told[name] = value
    env = {**os.environ, **told}
    env.update({name: str(new) for name, (_, new) in ports.items()})
    env["COMPOSE_PROJECT_NAME"] = f"{manifest().get('name', ROOT.name)}-try"
    off = turned_off()
    for key in flag_keys(where):
        spelled = key.upper().replace("-", "_")
        value = "off" if key in off else "on"
        env[f"FLAG_{spelled}"] = value
        env[f"VITE_FLAG_{spelled}"] = value
    env.pop("WEB_HOST", None)
    return env


# ---- the record the board reads -----------------------------------------------------------------------------

def read_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "stopped"}


def write_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    held = STATE.with_suffix(".tmp")
    held.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    held.replace(STATE)


def step(state: dict, said: str) -> None:
    state.setdefault("steps", []).append(said)
    state["step"] = said
    write_state(state)
    print(said, flush=True)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def status() -> dict:
    """The state as the board should say it: a ready app with a process gone is a failed one."""
    state = read_state()
    if state.get("state") == "ready":
        gone = [name for name, pid in (state.get("pids") or {}).items() if not alive(int(pid))]
        if gone:
            state.update(state="failed", error=f"{', '.join(gone)} stopped. Its log is in .slipwai/try-it/.")
    if state.get("state") == "starting" and not alive(int(state.get("runner", 0) or 0)):
        state.update(state="failed", error=f"stopped while {state.get('step', 'starting')}")
    commit = state.get("commit", "")
    if commit:
        state["behind"] = int(git("rev-list", "--count", f"{commit}..{trunk()}") or 0)
    return state


# ---- what a person is shown to try ---------------------------------------------------------------------------

def slice_quickstarts(commit: str) -> list[str]:
    listed = git("ls-tree", "-r", "--name-only", commit, "--", "specs")
    return [path for path in listed.splitlines() if re.search(r"^specs/[^/]+/slices/[^/]+/quickstart\.md$", path)]


def things_to_try(commit: str, path: str) -> dict:
    """A slice's quickstart, as a card: its title and its numbered steps, which already say what to do."""
    text = git("show", f"{commit}:{path}")
    lines = text.splitlines()
    heading = next((line for line in lines if line.startswith("# ")), "")
    title = re.split(r"\s[—-]\s", heading, maxsplit=1)[-1].strip() if heading else ""
    steps: list[str] = []
    for line in lines:
        if line.startswith("#") and steps:
            break  # the steps a person takes come first; what follows a heading is for someone else
        numbered = re.match(r"^\d+\.\s+(.*)", line)
        if numbered:
            steps.append(numbered.group(1))
        elif steps and line.startswith("   ") and line.strip():
            steps[-1] += " " + line.strip()
    parts = path.split("/")
    # Who the slice's own example data signs in as, which is who a person should be to follow its steps.
    try:
        told = json.loads(git("show", f"{commit}:{path.rsplit('/', 1)[0]}/try-it.json") or "{}")
    except ValueError:
        told = {}
    return {"feature": parts[1], "slice": parts[3], "title": title, "steps": steps[:8],
            "as": str(told.get("as", "")) if isinstance(told, dict) else ""}


def whats_new(commit: str, previous: str) -> list[dict]:
    """The slices whose quickstart arrived or changed between the commit Try it showed before and this one;
    every merged slice the first time, when there is nothing before."""
    paths = slice_quickstarts(commit)
    if previous and previous != commit:
        changed = set(git("diff", "--name-only", previous, commit, "--", "specs").splitlines())
        paths = [path for path in paths if path in changed]
    return [things_to_try(commit, path) for path in paths]


# ---- the steps ------------------------------------------------------------------------------------------------

def run(argv: list[str], where: Path, env: dict[str, str], log: Path) -> None:
    with log.open("a", encoding="utf-8") as out:
        out.write(f"\n$ {' '.join(argv)}\n")
        out.flush()
        done = subprocess.run(argv, cwd=where, env=env, stdout=out, stderr=subprocess.STDOUT, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"`{' '.join(argv)}` failed; the last lines are in {log.relative_to(ROOT)}")


def tail(log: Path, lines: int = 12) -> list[str]:
    try:
        return log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def make_targets(where: Path) -> set[str]:
    path = where / "Makefile"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return set(re.findall(r"^([a-z][a-z0-9-]*):", text, re.M))


def place(commit: str) -> bool:
    """The workspace at `commit`, made where there is none. Whether its dependencies need installing: the
    first time, and whenever a file at the top of a package moved — a manifest or a lockfile, in any
    ecosystem, sits at the top of its package and never under its sources."""
    where = workspace()
    if not where.is_dir():
        git("worktree", "add", "--detach", str(where), commit)
        if not where.is_dir():
            raise RuntimeError(f"could not make the Try it workspace at {where}")
        return True
    before = git("rev-parse", "HEAD", where=where)
    if before == commit:
        return False
    subprocess.run(["git", "-C", str(where), "checkout", "--quiet", "--detach", "--force", commit],
                   capture_output=True, check=True)
    packages = where / str((manifest().get("layout") or {}).get("packages") or "packages")
    tops = {".", *(app["path"] for app in deployables())}
    if packages.is_dir():
        tops |= {str(path.relative_to(where)) for path in packages.iterdir() if path.is_dir()}
    changed = git("diff", "--name-only", before, commit, where=where).splitlines()
    return any(str(Path(path).parent) in tops for path in changed if not path.endswith(".md"))


def sign_in_server(where: Path, env: dict[str, str]) -> None:
    """Point the Try it sign-in server at the Try it ports: each client that sends a person back to a
    browser app sends them back to the moved one too, and allows a password grant so example data can be
    loaded as a user. Only this throwaway server is changed; the realm files are not."""
    held = keycloak(where)
    if not held or not held["variable"]:
        return
    base = f"http://localhost:{env[held['variable']]}"
    # Healthy is the management port listening; the admin realm answers a few seconds after.
    waited, token = time.monotonic(), ""
    while not token:
        try:
            token = post_form(f"{base}/realms/master/protocol/openid-connect/token",
                              {"grant_type": "password", "client_id": "admin-cli", "username": held["user"],
                               "password": held["password"]})["access_token"]
        except (OSError, ValueError, KeyError):
            if time.monotonic() - waited > 90:
                raise RuntimeError(f"the sign-in server at {base} did not let its admin in") from None
            time.sleep(2)
    webs = [(app["port"], app["port"] + offset()) for app in deployables() if app["kind"] == "web"]
    for realm in realms(where):
        name = realm.get("realm", "")
        for client in request("GET", f"{base}/admin/realms/{name}/clients", token=token) or []:
            uris = client.get("redirectUris") or []
            if not any(f"localhost:{old}" in uri for uri in uris for old, _ in webs):
                continue
            moved = lambda values: sorted({*values, *(v.replace(f"localhost:{old}", f"localhost:{new}")
                                                      for v in values for old, new in webs)})
            client["redirectUris"] = moved(uris)
            client["webOrigins"] = moved(client.get("webOrigins") or [])
            attributes = client.get("attributes") or {}
            logout = attributes.get("post.logout.redirect.uris", "")
            if logout:
                attributes["post.logout.redirect.uris"] = "##".join(moved(logout.split("##")))
            client["attributes"] = attributes
            client["directAccessGrantsEnabled"] = True
            request("PUT", f"{base}/admin/realms/{name}/clients/{client['id']}", client, token=token)
            # Keycloak 25 moved `sub` into the `basic` scope, and a client whose scopes were listed before
            # that issues tokens without one — which a service keyed on `sub` refuses, every time.
            if "basic" not in (client.get("defaultClientScopes") or []):
                basic = next((one["id"] for one in request("GET", f"{base}/admin/realms/{name}/client-scopes",
                                                           token=token) or [] if one.get("name") == "basic"), "")
                if basic:
                    request("PUT", f"{base}/admin/realms/{name}/clients/{client['id']}/default-client-scopes/"
                                   f"{basic}", token=token)


def start_apps(where: Path, env: dict[str, str], state: dict) -> None:
    ports = {app["name"]: app["port"] + offset() for app in deployables()}
    pids = {}
    for app in deployables():
        mine = dict(env)
        mine[app["variable"]] = str(ports[app["name"]])
        if app["kind"] == "service":
            mine["PORT"] = str(ports[app["name"]])
        elif app["api"] in ports:
            mine["API_ORIGIN"] = f"http://localhost:{ports[app['api']]}"
        log = HOME / f"{app['name']}.log"
        out = log.open("w", encoding="utf-8")
        child = subprocess.Popen(["make", app["target"]], cwd=where, env=mine, stdout=out, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        pids[app["name"]] = child.pid
    state["pids"] = pids
    write_state(state)
    for app in deployables():
        address = f"http://localhost:{ports[app['name']]}" + ("/health" if app["kind"] == "service" else "/")
        waited = time.monotonic()
        while not answers(address):
            if not alive(pids[app["name"]]):
                raise RuntimeError(f"{app['name']} stopped before it answered: "
                                   + " / ".join(tail(HOME / f"{app['name']}.log", 3)))
            if time.monotonic() - waited > PATIENCE:
                raise RuntimeError(f"{app['name']} did not answer at {address} within {PATIENCE}s")
            time.sleep(2)


def stop_apps(state: dict) -> None:
    for pid in (state.get("pids") or {}).values():
        try:
            os.killpg(int(pid), signal.SIGTERM)
        except (OSError, ValueError):
            continue
    deadline = time.monotonic() + 8
    while any(alive(int(pid)) for pid in (state.get("pids") or {}).values()) and time.monotonic() < deadline:
        time.sleep(0.3)
    for pid in (state.get("pids") or {}).values():
        try:
            os.killpg(int(pid), signal.SIGKILL)
        except (OSError, ValueError):
            continue
    state["pids"] = {}


# ---- HTTP, with nothing but the standard library ------------------------------------------------------------

def answers(address: str) -> bool:
    try:
        with urllib.request.urlopen(address, timeout=3) as reply:
            return reply.status < 500
    except urllib.error.HTTPError as refused:
        return refused.code < 500
    except (OSError, ValueError):
        return False


def request(method: str, address: str, body: object = None, token: str = "", headers: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    sent = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {}),
            **(headers or {})}
    asked = urllib.request.Request(address, data=data, method=method, headers=sent)
    with urllib.request.urlopen(asked, timeout=20) as reply:
        raw = reply.read()
    return json.loads(raw) if raw.strip() else None


def post_form(address: str, fields: dict[str, str]) -> dict:
    asked = urllib.request.Request(address, data=urllib.parse.urlencode(fields).encode(), method="POST",
                                   headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(asked, timeout=20) as reply:
        return json.loads(reply.read())


# ---- example data ----------------------------------------------------------------------------------------------

def scenarios(where: Path) -> list[tuple[str, Path]]:
    """Every slice's `try-it.json`, in slice order."""
    found = sorted(where.glob("specs/*/slices/*/try-it.json"), key=lambda path: (path.parts[-4], path.parts[-2]))
    return [(f"{path.parts[-4]}/{path.parts[-2]}", path) for path in found]


def token_for(username: str, env: dict[str, str], where: Path) -> str:
    """A token for one of the fixture users, from the realm the service trusts, through the browser app's
    own client — so the token is the one that person would have had."""
    person = next((one for one in people(where) if one["username"] == username), None)
    if person is None:
        raise RuntimeError(f"no fixture user {username} in docker/keycloak/realms")
    realm = next(r for r in realms(where) if r.get("realm") == person["realm"])
    issuer = next((value for name, value in env.items() if name.endswith("OIDC_ISSUER")
                   and value.rstrip("/").endswith(f"/realms/{person['realm']}")), "")
    if not issuer:
        held = keycloak(where)
        issuer = f"http://localhost:{env.get(held.get('variable', ''), '')}/realms/{person['realm']}"
    client = next((c["clientId"] for c in realm.get("clients") or [] if c.get("publicClient")
                   and c.get("redirectUris")), "")
    return post_form(f"{issuer.rstrip('/')}/protocol/openid-connect/token",
                     {"grant_type": "password", "client_id": client, "username": username,
                      "password": person["password"], "scope": "openid email profile"})["access_token"]


def filled(value: object, kept: dict[str, object]) -> object:
    """A step's path or body with `{name}` replaced by what an earlier step kept."""
    if isinstance(value, str):
        whole = re.fullmatch(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", value)
        if whole and whole.group(1) in kept:
            return kept[whole.group(1)]
        return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", lambda m: str(kept.get(m.group(1), m.group(0))), value)
    if isinstance(value, list):
        return [filled(one, kept) for one in value]
    if isinstance(value, dict):
        return {key: filled(one, kept) for key, one in value.items()}
    return value


def picked(answer: object, path: str) -> object:
    for part in path.split("."):
        if isinstance(answer, dict):
            answer = answer.get(part)
        elif isinstance(answer, list) and part.isdigit() and int(part) < len(answer):
            answer = answer[int(part)]
        else:
            return None
    return answer


def seed(where: Path, env: dict[str, str], state: dict, only_new: bool, api: str = "", only: str = "") -> None:
    """Each slice's story, through the API, as the person it names. One that fails stops that slice's story
    and no other's: the rest of the data is still worth having, and the failure names what refused it.

    `api` and `only` are a slice checking its own story before it merges: against the app its berth runs,
    not Try it's, which has none of its routes yet."""
    service = next((app for app in deployables() if app["kind"] == "service"), None)
    if service is None:
        return
    base = api.rstrip("/") or f"http://localhost:{service['port'] + offset()}"
    done = set(state.get("seeded", [])) if only_new else set()
    failed = [] if not only_new else list(state.get("seed_failed", []))
    links = list(state.get("links", [])) if only_new else []
    tokens: dict[str, str] = {}
    for name, path in scenarios(where):
        if name in done or (only and name.rsplit("/", 1)[-1] != only):
            continue
        try:
            story = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as fault:
            failed.append({"slice": name, "step": "", "said": f"try-it.json is not JSON: {fault}"})
            continue
        kept: dict[str, object] = {}
        for number, one in enumerate(story.get("steps") or [], start=1):
            who = one.get("as") or story.get("as", "")
            try:
                if who and who not in tokens:
                    tokens[who] = token_for(who, env, where)
                headers = {"Idempotency-Key": str(uuid.uuid4()), **(one.get("headers") or {})}
                answer = request(one.get("method", "GET"), base + str(filled(one["path"], kept)),
                                 filled(one.get("body"), kept), tokens.get(who, ""), filled(headers, kept))
            except urllib.error.HTTPError as refused:
                said = refused.read().decode(errors="replace")[:300]
                refused.close()
                failed.append({"slice": name, "step": one.get("say") or f"step {number}",
                               "said": f"{refused.code} {said}"})
                break
            except (OSError, RuntimeError, KeyError, ValueError) as fault:
                failed.append({"slice": name, "step": one.get("say") or f"step {number}", "said": str(fault)})
                break
            for key, at in (one.get("keep") or {}).items():
                kept[key] = picked(answer, at)
        else:
            done.add(name)
            # Where in the browser app the story's records are: an app with no list of them has no other way
            # to reach what was just made.
            for opened in story.get("open") or []:
                links.append({"slice": name, "label": str(opened.get("label", "")),
                              "path": str(filled(opened.get("path", "/"), kept)),
                              "as": str(opened.get("as") or story.get("as", ""))})
    state["seeded"] = sorted(done)
    state["seed_failed"] = failed
    state["links"] = links
    write_state(state)


# ---- the verbs -----------------------------------------------------------------------------------------------

def begin(verb: str) -> tuple[dict, Path]:
    HOME.mkdir(parents=True, exist_ok=True)
    state = read_state()
    if state.get("state") == "starting" and alive(int(state.get("runner", 0) or 0)) \
            and int(state["runner"]) != os.getpid():
        raise SystemExit(f"Try it is already {state.get('step', 'starting')}; wait for it")
    log = HOME / "try-it.log"
    log.write_text(f"{verb} at {time.strftime('%Y-%m-%dT%H:%M:%S')}\n", encoding="utf-8")
    return state, log


def up(state: dict, log: Path, fresh: bool, keep_data: bool) -> None:
    where = workspace()
    commit = git("rev-parse", trunk())
    previous = state.get("commit", "")
    state.update(state="starting", runner=os.getpid(), commit=commit, steps=[], error="",
                 previous=previous if previous and previous != commit else state.get("previous", ""),
                 started=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    if not keep_data:
        state.update(seeded=[], seed_failed=[])
    write_state(state)
    try:
        install = place(commit)
        step(state, f"workspace at {commit[:7]}")
        env = environment(where)
        targets = make_targets(where)
        if install and "install" in targets:
            step(state, "installing dependencies")
            run(["make", "install"], where, env, log)
        if (where / "docker-compose.yml").is_file():
            if fresh:
                run(["docker", "compose", "down", "--volumes"], where, env, log)
            step(state, "starting the database and sign-in")
            run(["docker", "compose", "up", "-d", "--wait"], where, env, log)
            sign_in_server(where, env)
        if "migrate" in targets:
            step(state, "applying migrations")
            run(["make", "migrate"], where, env, log)
        step(state, "starting the app")
        start_apps(where, env, state)
        if scenarios(where):
            step(state, "loading example data")
            seed(where, env, state, only_new=keep_data)
        web = next((app for app in deployables() if app["kind"] == "web"), None)
        service = next((app for app in deployables() if app["kind"] == "service"), None)
        shown = web or service
        state.update(state="ready", step="ready", people=people(where), flags=flag_states(where),
                     new=whats_new(commit, state.get("previous", "")),
                     url=f"http://localhost:{shown['port'] + offset()}" if shown else "")
        write_state(state)
    except (RuntimeError, OSError, subprocess.CalledProcessError, KeyError, ValueError) as fault:
        state.update(state="failed", error=str(fault), log=tail(log))
        write_state(state)
        raise SystemExit(str(fault)) from None


def down(state: dict, log: Path, forget: bool) -> None:
    stop_apps(state)
    where = workspace()
    if (where / "docker-compose.yml").is_file():
        env = environment(where)
        run(["docker", "compose", "down", *(["--volumes"] if forget else [])], where, env, log)
    state.update(state="stopped", step="", runner=0, error="")
    write_state(state)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("verb", choices=("start", "refresh", "fresh", "stop", "status", "seed", "flag", "walks"))
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--slice", default="", help="seed: only this slice's story, from this checkout")
    parser.add_argument("--api", default="", help="seed --slice: the service to load it into, e.g. a berth's")
    asked = parser.parse_args(argv)
    if asked.verb == "seed" and asked.slice:
        # A slice's own check, before it merges: its story from this checkout, into the app it runs, with
        # the settings this checkout has — nothing moved, nothing recorded in Try it's state.
        held: dict = {}
        env = {**os.environ, **settings_file(ROOT / ".env.example"), **settings_file(ROOT / ".env")}
        seed(ROOT, env, held, only_new=False, api=asked.api, only=asked.slice)
        print(json.dumps({"seeded": held["seeded"], "failed": held["seed_failed"], "links": held["links"]},
                         indent=2))
        return 1 if held["seed_failed"] or not held["seeded"] else 0
    if asked.verb == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if asked.verb == "walks":
        print(walks())
        return 0
    state, log = begin(asked.verb)
    if asked.verb == "flag":
        key, value = (asked.rest + ["", ""])[:2]
        off = turned_off()
        off = off - {key} if value == "on" else off | {key}
        FLAGS.write_text(json.dumps(sorted(off)) + "\n", encoding="utf-8")
        if state.get("state") == "ready":
            stop_apps(state)
            state.update(state="starting", runner=os.getpid())
            step(state, f"restarting the app with {key} {value}")
            start_apps(workspace(), environment(workspace()), state)
            state.update(state="ready", step="ready", flags=flag_states(workspace()))
            write_state(state)
        return 0
    if asked.verb == "stop":
        down(state, log, forget=False)
        print("Try it stopped")
        return 0
    if asked.verb == "seed":
        # Only what is not loaded yet: a story run twice is a second record, which the app may rightly refuse.
        seed(workspace(), environment(workspace()), state, only_new=True)
        print(json.dumps({"seeded": state["seeded"], "failed": state["seed_failed"]}, indent=2))
        return 1 if state["seed_failed"] else 0
    if asked.verb in ("refresh", "fresh") or state.get("state") in ("ready", "failed"):
        stop_apps(state)
    # Data is kept across a stop and a refresh, so only slices not yet seeded are; a fresh start forgets it.
    up(state, log, fresh=asked.verb == "fresh", keep_data=asked.verb != "fresh")
    print(f"Try it is ready at {state['url']}")
    for person in state.get("people") or []:
        print(f"  sign in as {person['username']} / {person['password']}  ({person['name']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
