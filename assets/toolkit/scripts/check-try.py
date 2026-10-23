#!/usr/bin/env python3
"""Hold every slice's `try-it.json` to what it would need to seed, with no app running. `make verify` runs this.

On recap's second day 22 of 22 stories failed to seed and nothing had said so before the merge: seven stories
signed in as `ada` and `ines`, people the plan stage invented for the quickstart and no realm held; the rest
opened on screens two unbuilt slices would mount. Each was written at the Demo rung by a slice that had read
*uses the quickstart's synthetic people* and *one the service refuses is fixed here*, and nothing checked
either sentence. This is the static half of that check — what can be read off the files — and the live half
is the Demo rung's seed, which writes the `seeded` deck line the captain holds the slice to.

Four things, each a sentence naming the story:

1. **Every story parses** into the shape `TRY_STORY` describes, and says nothing a story has no use for.
2. **Every `as` names somebody**: a user of a realm under `docker/keycloak/realms/` with a password, or a
   person under `specs/<feature>/people/`. A person file with no username, name, password or realm is
   refused, and so is one whose username a realm already has — two passwords for one name.
3. **Every `open` path starts with a route the browser app mounts**, read from the app's own route table
   the way `try_it.flag_keys` reads its flags. A project with no browser app skips this one.
4. **Every `given` event is one the model types**: a mark on the chart, an event frame in the model, and —
   where the frame declares `attributes` — only those names, with every identifying one present. A story
   never gives what its own slice sets, and the standard profile has no `given` at all.

The rules live in `scripts/agents/try_it.py`, which is the thing that seeds; this gate loads it by path and
asks, so the words it refuses a story with are the words the seed would have failed on.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


HERE = Path(__file__).resolve()
ROOT = project_root(HERE)
SPECS = ROOT / "specs"
MODEL = HERE.parents[1] / "docs/event-model/model.yaml"
FIX = "python3 scripts/check-try.py"


def try_it_module():
    """`scripts/agents/try_it.py`, loaded the way a project runs it: by path, beside this gate."""
    path = HERE.parent / "agents/try_it.py"
    spec = importlib.util.spec_from_file_location("try_it_gate", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"check-try: {path} is not here. Run `slipwai migrate` to restore it")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def model_events() -> dict[str, list[dict]] | None:
    """Each event the model types, with its declared attributes (an empty list where the frame carries
    prose `data` alone). None where there is no model, which is the standard profile."""
    if not MODEL.is_file():
        return None
    loaded = load_yaml(MODEL.read_text(encoding="utf-8"))
    found: dict[str, list[dict]] = {}
    for item in (loaded.get("slices") if isinstance(loaded, dict) else None) or []:
        for frame in (item.get("frames") if isinstance(item, dict) else None) or []:
            if isinstance(frame, dict) and frame.get("type") == "evt" and frame.get("name"):
                attributes = frame.get("attributes")
                found.setdefault(str(frame["name"]), [one for one in attributes if isinstance(one, dict)]
                                 if isinstance(attributes, list) else [])
    return found


def chart_sets(feature: str) -> dict[str, list[str]]:
    """Each charted slice's `sets`, so a story cannot give what its own slice sets."""
    path = SPECS / feature / "chart.yaml"
    if not path.is_file():
        return {}
    loaded = load_yaml(path.read_text(encoding="utf-8"))
    slices = loaded.get("slices") if isinstance(loaded, dict) else None
    return {str(slice_id): [str(mark) for mark in (body or {}).get("sets") or []]
            for slice_id, body in (slices or {}).items() if isinstance(body, dict)}


def people_faults(try_it) -> tuple[set[str], list[str]]:
    """Every username a story may sign in as, and why a people file is refused."""
    said: list[str] = []
    realm = {one["username"] for one in try_it.realm_people(ROOT)}
    known = set(realm)
    for person in try_it.declared_people(ROOT):
        if "fault" in person:
            said.append(f"{person['source']}: {person['fault']}; a person is "
                        f"{{{', '.join(repr(key) for key in try_it.PERSON_FIELDS)}}}")
        elif person["username"] in realm:
            said.append(f"{person['source']}: {person['username']} is already a user of the realm; the realm's "
                        f"password stands, so this file says nothing and is refused")
        else:
            known.add(person["username"])
    return known, said


def main() -> int:
    try_it = try_it_module()
    stories = try_it.scenarios(ROOT)
    known, faults = people_faults(try_it)
    mounted_routes = try_it.routes(ROOT)
    events = model_events()
    sets_by_feature: dict[str, dict[str, list[str]]] = {}
    for name, path in stories:
        feature, slice_id = name.split("/", 1)
        try:
            story = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as fault:
            faults.append(f"{name}: try-it.json is not JSON ({fault})")
            continue
        sets = sets_by_feature.setdefault(feature, chart_sets(feature)).get(slice_id, [])
        faults += try_it.story_faults(name, story, known, mounted_routes, sets, events)
    if faults:
        print(f"check-try: {len(faults)} thing(s) would stop a story seeding, read off the files alone",
              file=sys.stderr)
        for fault in faults:
            print(f"  {fault}", file=sys.stderr)
        print(f"  Fix the story or declare the person under specs/<feature>/people/, then: {FIX}", file=sys.stderr)
        return 1
    screens = "no browser app, so no screen check" if mounted_routes is None else f"{len(mounted_routes)} routes"
    print(f"check-try: {len(stories)} stor{'y' if len(stories) == 1 else 'ies'} seedable on paper — "
          f"{len(known)} people to sign in as, {screens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
