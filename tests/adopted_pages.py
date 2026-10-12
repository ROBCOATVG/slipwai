"""The matrix every page and block an *adopted* repository receives is rendered across, and its digests.

Not a test module — `unittest discover` collects `test_*.py` only. This is the reading
`test_adopted_pages.py` compares against `tests/fixtures/adopted-pages.sha256`, and it is a file rather
than a one-liner because the pages `project/adopted.py` and `project/sail_adoption.py` write branch on
seven things at once: the forge that runs CI, how a change reaches production, whether the repository had
a `Makefile`, whether it has converged, where the delivery material sits, what was wrapped and in which
language, and where the schema and the infrastructure live.

The command pages these two modules also reach — `commands/sail.md`, whose ladder gains the adoption's
three stages — are recorded in `tests/fixtures/command-pages.sha256` already, by `command_pages.py`, and
are deliberately not recorded twice here.

Run it to take the reading:

    PYTHONPATH=src:tests python3 tests/adopted_pages.py

Every case is named, and the name is what the record's middle column carries, so a row that fails says
which repository the page belonged to rather than only which file.
"""
from __future__ import annotations

import hashlib

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.layout import AT_ROOT, Layout
from slipwai.origin import Adoption
from slipwai.project.adopted import adoption_page, agents_block, gitignore_block, makefile_block
from slipwai.project.cruise import cruise_config
from slipwai.project.sail_adoption import adoption_hooks
from slipwai.services import App

#: The version the block names. Fixed here so the record is a reading of the prose and not of `VERSION`,
#: which moves every release and would make every row of this file stale for a reason nobody cares about.
VERSION = "1.13.0"
#: What `adopt` appends to the repository's own `.gitignore`: what the delivery material writes.
IGNORED = "# what the delivery material writes\n.delivery-tools/\nbaseline.json\nnode_modules/\n"
#: The hooks file as `assets/toolkit/` ships it, which the adoption appends its own three hooks to.
EXTENSIONS = (TOOLKIT_ROOT / ".specify/extensions.yml").read_text(encoding="utf-8")


def wrapped(
    name: str = "shop", path: str = ".", language: str = "javascript", kind: str = "service",
    commands: dict | None = None, toolchain: dict | None = None, purpose: str | None = None,
) -> App:
    """An application that was here before the method was — what these pages are written about."""
    return App(name, path, kind, language, None, 0, generated=False, purpose=purpose,
               commands={"test": "npm test", "lint": None} if commands is None else commands,
               toolchain={"kind": "node", "version": "20", "ecosystem": "npm", "packaging": "npm"}
               if toolchain is None else toolchain,
               provenance={"kind": "confirmed", "commands": "detected"})


HERE = {"schema": "here", "tools": ["flyway"], "provenance": "confirmed"}
ELSEWHERE = {"schema": "elsewhere", "repository": "git@example.com:shop/db.git", "provenance": "detected"}
UNMANAGED = {"schema": "unmanaged", "provenance": "detected"}
INFRA_HERE = {"home": "here", "describedBy": ["terraform"], "provenance": "confirmed"}
INFRA_NONE = {"home": "none", "provenance": "detected"}
INFRA_ELSEWHERE = {"home": "elsewhere", "repository": "git@example.com:shop/infra.git", "provenance": "detected"}

#: One entry per repository the pages are rendered for. Between them they reach every branch the two
#: modules make: each of the five forges, each of the four release paths, a repository that had a
#: `Makefile` and one that had none, both delivery layouts, a converged repository, a language the keel
#: generates and one it does not, an adoption with no application wrapped at all, and each home an answer
#: can take for the schema and the infrastructure.
CASES: dict[str, dict] = {
    "github-pipeline": dict(
        apps=[wrapped()], layout=Layout("delivery"),
        adoption=Adoption(
            why="the runtime is out of support", database=HERE, infrastructure=INFRA_HERE,
            survey={"makefile": True, "readme": True},
            ci={"forge": "github", "gate": ".github/workflows/verify-delivery.yml", "branch": "main",
                "evidence": ".github/workflows/ci.yml", "provenance": "confirmed"},
            release={"path": "pipeline", "evidence": [".github/workflows/deploy.yml"],
                     "provenance": "confirmed"})),
    "gitlab-scripted": dict(
        apps=[wrapped("billing", "services/billing", "python", "library", purpose="invoices")],
        layout=AT_ROOT,
        adoption=Adoption(
            database=ELSEWHERE, infrastructure=INFRA_ELSEWHERE, survey={"makefile": False},
            ci={"forge": "gitlab", "gate": ".gitlab/delivery.yml", "evidence": ".gitlab-ci.yml",
                "provenance": "detected"},
            release={"path": "scripted", "evidence": ["deploy.sh"], "provenance": "detected"})),
    "gitea-manual": dict(
        apps=[wrapped("tools", "tools", "go", "tool", commands={"test": "go test ./...", "smoke": None},
                      toolchain={"kind": "go", "version": "1.22"})],
        layout=Layout("delivery"),
        adoption=Adoption(
            why="we cannot hire for it", database=UNMANAGED, infrastructure=INFRA_NONE,
            survey={"makefile": True},
            ci={"forge": "gitea", "gate": ".gitea/workflows/verify-delivery.yml", "provenance": "detected"},
            release={"path": "manual", "provenance": "confirmed"})),
    "other-forge-unknown": dict(
        apps=[wrapped("legacy", "src", "cobol", "application", commands={"test": None}, toolchain={})],
        layout=AT_ROOT,
        adoption=Adoption(
            database={}, infrastructure={}, survey={},
            ci={"forge": "other", "gate": None, "evidence": "Jenkinsfile", "provenance": "detected"},
            release={})),
    "no-ci-nothing-wrapped": dict(
        apps=[], layout=AT_ROOT,
        adoption=Adoption(
            database={"schema": "none"}, infrastructure={"home": "unmanaged"}, survey={"makefile": False},
            ci={"forge": "none", "provenance": "detected"},
            release={"path": "unknown", "provenance": "unrecorded"})),
    "converged": dict(
        apps=[wrapped(), wrapped("web", "apps/web", "typescript", "service", purpose="the storefront")],
        layout=AT_ROOT,
        adoption=Adoption(
            why="cloud exit", database=HERE, infrastructure=INFRA_HERE, survey={"makefile": True},
            ci={"forge": "github", "gate": ".github/workflows/verify-delivery.yml", "provenance": "confirmed"},
            release={"path": "pipeline", "provenance": "confirmed"},
            converged={"with": "1.12.0", "from": "delivery"})),
}


def pages(case: str) -> dict[str, str]:
    """Every file and block an adopted repository receives from the two modules this slice moves."""
    given = CASES[case]
    apps, layout, adoption = given["apps"], given["layout"], given["adoption"]
    return {
        "docs/adoption.md": adoption_page("harbour-shop", apps, adoption, layout),
        ".specify/extensions.yml": adoption_hooks(EXTENSIONS, apps, layout),
        "AGENTS.md#delivery": agents_block(layout, VERSION),
        "Makefile#delivery": makefile_block(layout),
        ".gitignore#delivery": gitignore_block(IGNORED, layout),
        # Written into every project, generated and adopted alike; recorded here because `cruise.py` is this
        # slice's and nothing else digests the file it writes.
        ".specify/cruise.json": cruise_config(),
    }


def record() -> str:
    """The reading, one line per page: digest, case, path."""
    return "\n".join(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {case}  {path}"
        for case in CASES
        for path, text in sorted(pages(case).items())
    )


if __name__ == "__main__":  # pragma: no cover
    print(record())
