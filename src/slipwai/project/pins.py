"""The toolchain versions this project is pinned to, written where each ecosystem's own tools look for them.

CI and Compose already pinned a Node major and a CPython minor; a laptop was told nothing. So the gate ran on
24 and the person running `npm test` ran on whatever their shell had last selected, and the difference showed
up as a failure in CI that did not reproduce. These files are how each ecosystem spells "this repository wants
that version", and every one of them is *derived* from the constant the CI workflow and the image build
already read (`backends.NODE_MAJOR`, `backends.PYTHON_VERSION`) — a pin file with a number typed into it
would be a second copy of a version, which is a version already wrong somewhere.

**`.nvmrc`, not `.node-version`.** Both are one line holding a version, and the question is only which more
tools read. `.nvmrc` is read by nvm, fnm, asdf, mise and Volta, and is what `actions/setup-node`'s
`node-version-file` is documented against; `.node-version` is read by nodenv, fnm, asdf and mise, but not by
nvm or Volta — the two with the largest installed base. So `.nvmrc` is the file a contributor's existing
tooling is likeliest to already honour, and it is also the one this factory's own `survey.py` reads first when
it is looking at somebody else's repository.

Only two languages take a file of their own, because only two need one. Go pins its toolchain in `go.mod`'s
own `go` directive — which is why the CI step reads `go-version-file: <service>/go.mod` rather than a number —
and Java pins its build through the committed Maven wrapper and the `java-version` its CI step names. Adding
a `.go-version` or a `.java-version` beside those would be a second answer to a question already answered, and
the first thing to drift.

`.editorconfig` is written whole rather than per language present, and that is deliberate. It describes how a
file of a given type is written, not what this project contains, so a section for a language the project has
no files in costs nothing and is right the moment `add-service` adds one — whereas a conditional
`.editorconfig` would be a file every later command had to remember to regenerate. Every generated project
also has `scripts/*.py` and YAML workflows whatever its services are written in.
"""
from __future__ import annotations

from ..backends import NODE_MAJOR, PYTHON_VERSION
from ..services import App, families_of
from .shared_packages import node_workspace

# The Spec Kit release `./init` installs, recorded in `project.json` as `speckitSource` so that restoring the
# gitignored projections later is a reinstall at the same version rather than a silent move to upstream HEAD —
# which took one project from 1.0.6 to 1.0.9.dev0 while it was only asking for its commands back, and made
# `check-speckit` read every projected skill as edited in place. Raising it here reaches every project through
# `slipwai migrate`, as a diff the project decides.
SPECKIT_TAG = "v1.0.8"
SPECKIT_SOURCE = f"git+https://github.com/github/spec-kit.git@{SPECKIT_TAG}"

# What EditorConfig says about a file of each kind here. Two spaces as the house default because that is what
# every formatter in this project's toolchain already emits (Prettier, Biome, the YAML this factory writes);
# four for Python and Java, which is what PEP 8 and every Java convention ask; tabs for Go, which `gofmt`
# writes and will rewrite, and for Make, where a space-indented recipe is a syntax error rather than a style.
# `trim_trailing_whitespace` is off for Markdown alone, where two trailing spaces are a hard line break.
EDITORCONFIG = """# The whitespace conventions of this repository, for editors that read them.
# https://editorconfig.org — supported natively by most editors and through a plugin by the rest.
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.{py,java}]
indent_size = 4

[*.go]
indent_style = tab

[Makefile]
# Not a preference: GNU Make requires a tab at the start of a recipe line.
indent_style = tab

[*.md]
# Two trailing spaces are a hard line break in Markdown.
trim_trailing_whitespace = false
"""


def pin_files(apps: list[App]) -> dict[str, str]:
    """The pin files this project's toolchains have, keyed by path.

    At the repository root rather than beside each service: every one of these tools walks up from the
    working directory, so one file at the top answers for a service directory too — and a project with two
    Python services is pinned to one CPython, which is what `go.work`, the npm workspace and the single CI
    `setup-python` step already assume.
    """
    families = families_of(apps)
    files = {".editorconfig": EDITORCONFIG}
    if node_workspace(apps):
        files[".nvmrc"] = f"{NODE_MAJOR}\n"
    if "python" in families:
        files[".python-version"] = f"{PYTHON_VERSION}\n"
    return files


def pin_list(apps: list[App]) -> str:
    """The pin files this project has, as prose — read off the set that actually ships, so a page cannot
    name one a project was not given."""
    return ", ".join(f"`{path}`" for path in pin_files(apps))
