"""Which feature is in hand, and whether the model and the split hold *that* feature yet.

Every stage above the chart once asked whether the project had the artifact: a model that names a slice, a
chart that names one, a storyboard anywhere under `specs/`. A first feature answers yes to all three for
every feature after it, so a further feature that had only its specification was launched straight past its
storyboard, its model and its split: the launch read the finished feature's chart, cast off a fleet with
nothing to start, and said it had continued the build.

The model is global and there is one chart per project, so a slice says which feature it belongs to
(`feature: <the directory under specs/>`), and the chart carries it. A slice that says nothing belongs to
the feature the chart is written under — which is every slice written before this, so a project with one
feature reads exactly as it did.

Read as text, as `passage.names_slices` is and for its reason: the keel reads no YAML.

Carried into a generated project as `scripts/agents/feature_stages.py` (`scripts/shared-modules.py`), where
`launch.py`, `model.py` and `surfaces.py` ask the same questions: one reading, or the board and the script it
runs disagree about whether a feature is split. So this imports nothing but the standard library.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MODEL = "docs/event-model/model.yaml"
_FEATURE = re.compile(r"feature:\s*(?P<name>.*?)\s*$")


def specifications(root: Path) -> list[Path]:
    specs = root / "specs"
    return sorted(specs.glob("*/spec.md")) if specs.is_dir() else []


def charts(root: Path) -> list[Path]:
    specs = root / "specs"
    return sorted(specs.glob("*/chart.yaml")) if specs.is_dir() else []


def in_hand(root: Path) -> Path | None:
    """The feature the steps above the chart are about: the one `.specify/feature.json` names, else the only
    specification no chart holds yet, else the only specification; None where nothing says which."""
    try:
        held = json.loads((root / ".specify/feature.json").read_text(encoding="utf-8"))
        named = (root / str(held.get("feature_directory") or "")).resolve()
        if named.is_relative_to(root.resolve()) and (named / "spec.md").is_file():
            return named
    except (OSError, ValueError, AttributeError):
        pass
    specs = specifications(root)
    uncharted = [path.parent for path in specs if not (path.parent / "chart.yaml").is_file()]
    if len(uncharted) == 1:
        return uncharted[0]
    return specs[0].parent if len(specs) == 1 else None


def name_in_hand(root: Path) -> str:
    """`in_hand` by its directory name, or `""`."""
    found = in_hand(root)
    return found.name if found is not None else ""


def claims(page: Path) -> tuple[set[str], bool]:
    """The features a model's or a chart's slices name, and whether any slice names none.

    A model lists its slices (`- id: S1`), a chart maps them by id; both are read. `feature:` counts only as
    a slice's own key, never one nested inside a frame.
    """
    try:
        text = page.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set(), False
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    start = next((index for index, line in enumerate(lines) if line.startswith("slices:")), None)
    if start is None:
        return set(), False
    rest = lines[start].partition(":")[2].strip()
    if rest:  # written on one line: nothing in it can be read as a slice's own key
        return set(), rest not in ("[]", "{}", "null", "~")
    block: list[str] = []
    for line in lines[start + 1:]:
        if not line.startswith((" ", "-")):
            break
        block.append(line)
    if not block:
        return set(), False
    depth = len(block[0]) - len(block[0].lstrip())
    listed = block[0].lstrip().startswith("-")
    items: list[list[str]] = []
    for line in block:
        indent = len(line) - len(line.lstrip())
        if indent == depth and (not listed or line.lstrip().startswith("-")):
            # A list item's first key is on the line with the dash; read it where its other keys are.
            items.append([" " * (depth + 2) + line.lstrip()[1:].lstrip()] if listed else [])
        elif items:
            items[-1].append(line)
    named: set[str] = set()
    unnamed = False
    for item in items:
        keys = min((len(line) - len(line.lstrip()) for line in item), default=0)
        said = ""
        for line in item:
            found = _FEATURE.match(line.strip()) if len(line) - len(line.lstrip()) == keys else None
            if found:
                said = found.group("name").strip("'\"")
        if said and said not in ("null", "~"):
            named.add(said)
        else:
            unnamed = True
    return named, unnamed


def home(root: Path) -> str:
    """The feature the slices that name none belong to: the one the chart is written under, else the first
    with a specification. A chart under a directory with no specification (`specs/model/`) is nobody's."""
    for chart in charts(root):
        if any(claims(chart)) and (chart.parent / "spec.md").is_file():
            return chart.parent.name
    specs = specifications(root)
    return specs[0].parent.name if specs else ""


def modelled_for(root: Path, feature: str) -> bool:
    """Whether the event model holds a slice of `feature`."""
    named, unnamed = claims(root / MODEL)
    return bool(feature) and (feature in named or (unnamed and feature == home(root)))


def split_for(root: Path, feature: str) -> bool:
    """Whether a chart holds a slice of `feature`, which is what a captain is lit for."""
    if not feature:
        return False
    for chart in charts(root):
        named, unnamed = claims(chart)
        own = chart.parent.name if (chart.parent / "spec.md").is_file() else home(root)
        if feature in named or (unnamed and feature == own):
            return True
    return False


def approved_for(root: Path, feature: str) -> bool:
    """Whether a person has given `feature`'s storyboard its verdict and parked nothing: a state approved, or
    the written answer that it has no surface. What the model is made from, so what the model waits on."""
    try:
        said = (root / "specs" / feature / "mockups" / "mock-states.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(feature) and ("\u2014 approved" in said or "surfaces: none" in said) and "\u2014 parked" not in said
