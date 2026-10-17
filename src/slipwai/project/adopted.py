"""What a repository the keel did not make takes from it, and the pages and blocks that explain the adoption.

`scaffold.project_files` assembles the whole of a project as if the keel had made it; this cuts that set down for one
the method is installed around (brownfield adoption). Three root files are the repository's own and never claimed —
`README.md`, `AGENTS.md`, `.gitignore` — and `.claude/settings.json` is written only where there is none. What the
factory owes them is a marked block, appended once by `adopt` and left alone by `replay`, which regenerates only what is
listed in `<layout.delivery>/.written`: the paths it wrote, so that a newer factory can tell what to replace in a tree
that is mostly not its own. The CI workflow is `verify-delivery.yml`, beside whatever CI the repository runs, and sets
up the toolchains the wrapped applications recorded rather than the ones the catalog knows.
"""
from __future__ import annotations

from ..assets import ADOPTION_ROOT, VERSION
from ..catalog import CATALOG, families
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, wrapped_of
from .adopted_ci import ACTIONS_GATE, delivery_workflow, gitlab_job
from .prose import page
from .sail_adoption import adoption_hooks
from .shared_packages import PACKAGES

# The list of every path the keel wrote into an adopted repository, relative to the root. `replay` reads the
# previous one out of the commit it sits on, so what an older factory wrote and a newer one no longer does is
# removed rather than left behind.
WRITTEN = ".written"
# The repository's own files, which an adoption never writes over. `README.md`, `AGENTS.md` and `.gitignore` take
# a marked block instead; `.claude/settings.json` is written only where the repository has none; and `CLAUDE.md`,
# which a repository may already hold in its own words, gets its `@AGENTS.md` region from `make agents`, which
# writes that region into whatever is there rather than over it.
#
# The rest are the root files a repository that already exists has already answered for itself, and answered
# for its own reasons: which Node it is pinned to, how it indents, who it is licensed to, how a vulnerability
# reaches its maintainers, what a pull request into it has to say, and whether anything updates its
# dependencies. Every one of them would be wrong if the keel wrote it — a placeholder licence over a real
# one is the worst of them — and none is something the method needs in order to work.
OWN = (
    "README.md", "AGENTS.md", "CLAUDE.md", ".gitignore", ".claude/settings.json", f"{PACKAGES}/.gitkeep",
    ".editorconfig", ".nvmrc", ".python-version", "LICENSE", "SECURITY.md", "renovate.json",
    ".github/PULL_REQUEST_TEMPLATE.md",
)


def adopted_files(files: dict[str, str], apps: list[App], layout: Layout, adoption: Adoption) -> dict[str, str]:
    """The assembled and placed files, cut to what an adopted repository takes, with the list of them. The CI
    configuration is written for the forge the adoption recorded, or not at all — never a GitHub workflow into a
    repository whose CI is somewhere else; a record from before the forge was recorded gets the workflow."""
    kept = {path: content for path, content in files.items() if path not in OWN}
    kept.pop(".github/workflows/verify.yml", None)
    gate = adoption.ci.get("gate") if adoption.ci else ACTIONS_GATE
    if gate == ACTIONS_GATE:
        kept[gate] = delivery_workflow(apps, layout, (adoption.ci or {}).get("branch") or "main")
    elif gate:
        kept[gate] = gitlab_job(apps, layout)
    # Spec Kit reads its hooks at the root whatever the layout, so the file is not relocated; the adoption's own
    # hooks — the map before a specification, the pin before a plan, the map again after converge — go in it.
    kept[".specify/extensions.yml"] = adoption_hooks(kept[".specify/extensions.yml"], apps, layout)
    written = layout.under(WRITTEN)
    kept[written] = "".join(f"{path}\n" for path in sorted([*kept, written]))
    return kept


def unavailable(language: str) -> str:
    """What the keel cannot do for a language it cannot generate, said plainly."""
    if language in families():
        return (
            f"`{language}` is a language this factory generates, so `add-service --language {language}` can put a "
            "generated service beside the existing one, with every axis and gate a generated service has."
        )
    return (
        f"`{language}` is not a language this factory generates, so for this application there is no generated "
        "skeleton, no axis to answer (event store, HTTP transport, identity), no production image, no "
        "target and no hexagonal import rule — only the gate composed from its recorded commands, and the "
        "skills, commands and documentation, which speak of every language."
    )


def commands_table(app: App) -> str:
    rows = "\n".join(
        f"| `{target}` | {f'`{command}`' if command else '*none recorded — a written no; the target passes and says so*'} |"
        for target, command in (app.commands or {}).items()
    )
    return f"| Target | Command |\n|---|---|\n{rows}\n"


def home_paragraph(what: str, record: dict, key: str) -> str:
    home = record.get(key, "unknown")
    repository = record.get("repository")
    tools = record.get("tools") or record.get("describedBy") or []
    said = {
        "here": "versioned in this repository" + (f" ({', '.join(f'`{t}`' for t in tools)})" if tools else ""),
        "elsewhere": f"owned by another repository{f', `{repository}`' if repository else ''} — a contract between "
        "two repositories, which is what to test at the boundary",
        "unmanaged": "not versioned anywhere this survey could see: applied by hand, by a DBA or a console. The first "
        "step of the data or infrastructure work is a versioned baseline, described before it is imported",
        "none": "not part of this system",
    }.get(home, f"recorded as `{home}`")
    return f"**{what}** is {said} (`{record.get('provenance', 'detected')}`)."


def block_values(layout: Layout = AT_ROOT, version: str = VERSION) -> dict[str, str]:
    """Every value `assets/adoption/blocks/` may name. Its own set, not the page's: the block names the
    version that installed it and the page does not, and a pooled set would let either name the other's."""
    return {"where": where(layout), "make": layout.make, "written": WRITTEN, "version": version}


def values(
    project_name: str = "project", apps: list[App] | None = None, adoption: Adoption | None = None,
    layout: Layout = AT_ROOT,
) -> dict[str, str]:
    """Every value `assets/adoption/docs/adoption.md` may name, and the whole of what it may name.

    The four that are not a path or a name are each a sentence agreeing with a record rather than a
    paragraph somebody edits: what was wrapped, where the schema and the infrastructure live, where the
    gate runs in CI, and which step a repository that already had a `Makefile` is given. Each branches
    inside a sentence or inside a numbered item, which `docs/generated-prose.md` keeps in Python.
    """
    apps = [] if apps is None else apps
    adoption = Adoption() if adoption is None else adoption
    release = adoption.release
    evidence = ", ".join(f"`{one}`" for one in release.get("evidence") or [])
    return {
        "project": project_name,
        "where": where(layout),
        "make": layout.make,
        "written": WRITTEN,
        "backends": ", ".join(CATALOG["backends"]),
        "applications": applications(apps),
        "database": home_paragraph("The database schema", adoption.database, "schema"),
        "infrastructure": home_paragraph("The deployment infrastructure", adoption.infrastructure, "home"),
        "ci": ci_paragraph(adoption, layout),
        "makefile-step": makefile_step(adoption, layout),
        "why": adoption.why or "",
        "converged-with": str(adoption.converged.get("with")),
        "converged-from": str(adoption.converged.get("from")),
        "release-provenance": release.get("provenance", "unrecorded"),
        "release-evidence": f", from {evidence}" if evidence else "",
    }


def applications(apps: list[App]) -> str:
    """What was wrapped, one record at a time — read off `project.json`, never an asset's to hand-write."""
    return "\n\n".join(
        f"### `{app.path}` — `{app.name}`, {kind_phrase(app)} in {app.language}"
        + (f" ({app.toolchain.get('ecosystem')}{', ' + app.toolchain['packaging'] if app.toolchain.get('packaging') else ''}"
           f"{', ' + app.toolchain['kind'] + ' ' + app.toolchain['version'] if app.toolchain.get('version') else ''})"
           if app.toolchain else "")
        + (f"\n\n{app.purpose}" if app.purpose else "")
        + f"\n\nProvenance: {', '.join(f'{k} `{v}`' for k, v in app.provenance.items()) or 'none recorded'}.\n\n"
        + commands_table(app) + "\n" + unavailable(app.language)
        for app in wrapped_of(apps)
    ) or "No buildable directory was found, so nothing was wrapped: the gate is the method's own checks alone."


def makefile_step(adoption: Adoption, layout: Layout) -> str:
    """The fourth of *Next*: offer the targets, or say the `Makefile` `adopt` wrote is where they are.

    A branch inside a numbered item rather than around one — it begins after `4. ` — so `OPEN` and `CLOSE`,
    which are anchored to the start of a line, cannot mark it. It stays here and the asset carries the
    frame around it with a token (`docs/generated-prose.md`, *The branch*).
    """
    return (
        f"Offer the targets as the repository's own: add `-include {where(layout)}Makefile` to the root `Makefile`,\n"
        "   and `make verify` is one word again."
        if adoption.survey.get("makefile")
        else f"`make verify` is one word: the repository had no `Makefile`, so `adopt` wrote one that includes\n"
        f"   `{where(layout)}Makefile`, in a marked block. Targets of the repository's own go around it."
    )


def adoption_page(project_name: str, apps: list[App], adoption: Adoption, layout: Layout) -> str:
    """`docs/adoption.md`: what was wrapped, what that forfeits, where the facts came from, and what is next.

    Three of the page's branches are whole paragraphs and so are sections it carries: why this repository is
    being worked on, that it has converged, and which of the four things is true about how a change reaches
    production. The last is four sections of which exactly one is selected, the way `rules.py` carries one
    section per answer to an axis.
    """
    wanted = (*(("why",) if adoption.why else ()),
              *(("converged",) if adoption.converged else ()),
              f"release-{adoption.release.get('path', 'unknown')}")
    return page(ADOPTION_ROOT / "docs", "adoption.md", values(project_name, apps, adoption, layout), wanted)


def where(layout: Layout) -> str:
    """The delivery directory as a path prefix: `delivery/`, or nothing at the root."""
    return f"{layout.delivery}/" if layout.moved else ""



def kind_phrase(app: App) -> str:
    """How a page names what a wrapped application is: `a service`, `a library` — or that nobody has said."""
    return f"a {app.kind}" if app.kind != "application" else "an application whose role is not recorded"


def ci_paragraph(adoption: Adoption, layout: Layout) -> str:
    """The sentence about where the gate runs in CI, true to the forge that was recorded."""
    ci = adoption.ci
    forge, gate, provenance = ci.get("forge", "github"), ci.get("gate", ACTIONS_GATE), ci.get("provenance", "detected")
    if forge in ("github", "gitea"):
        runner = "GitHub Actions" if forge == "github" else "Gitea Actions"
        return (
            f"The same `verify` runs in CI from `{gate}` on {runner} (`{provenance}`), beside whatever CI this "
            "repository already had."
        )
    if forge == "gitlab":
        return (
            f"The same `verify` runs in CI as the GitLab job in `{gate}` (`{provenance}`) once `.gitlab-ci.yml` includes "
            f"it — `include: [local: {gate}]` — beside whatever jobs it already has; that edit is yours, since the "
            "file is."
        )
    if forge == "other":
        return (
            f"No CI configuration was written: this repository's CI (`{ci.get('evidence')}`, recorded as `other`, "
            f"`{provenance}`) is not one the factory can write a job for. Have it run `{layout.make} verify`; until it "
            "does, the gate runs on the machine that runs it and nowhere else."
        )
    return (
        f"No CI configuration was written: the survey found none in this repository (`{provenance}`). The gate runs "
        f"where somebody runs `{layout.make} verify`, and nowhere else, until a CI runs it — that is the first rung "
        "of the path to production, and `/sail` will ask about it."
    )



def agents_block(layout: Layout, version: str) -> str:
    """The marked section `adopt` appends to the repository's `AGENTS.md`, in the shape an extension's block has,
    so that a harness reading a copy of the file receives it too (`scripts/agents/project.py`).

    The markers stay here and the words are the asset's: `converge.py` matches this pair by name when it
    respells the block, so the pair is machinery rather than a paragraph anybody edits."""
    body = page(ADOPTION_ROOT / "blocks", "agents.md", block_values(layout, version))
    return f"\n<!-- extension:delivery:begin -->\n{body}<!-- extension:delivery:end -->\n"


def makefile_block(layout: Layout) -> str:
    """The root `Makefile` `adopt` writes where the repository has none, so that `make verify` is one word from
    the start. Marked like the other appended blocks: targets of the repository's own go around it."""
    return f"""# slipwai:delivery:begin — written by `slipwai adopt`, since this repository had no Makefile
# The delivery method's targets, offered as this repository's own: `make verify`, `make help`. Add targets of
# your own around this block, not inside it.
-include {where(layout)}Makefile
# slipwai:delivery:end
"""


def gitignore_block(ignored: str, layout: Layout) -> str:
    """The marked lines `adopt` appends to the repository's `.gitignore`: what the delivery material writes."""
    lines = "".join(f"{line}\n" for line in ignored.splitlines() if line and not line.startswith("#"))
    return f"\n# slipwai:delivery:begin — what the delivery material under {where(layout)} writes\n{lines}# slipwai:delivery:end\n"
