"""Where the factory's delivery material lives in a project, and how files assembled for one place go in another.

A generated repository keeps the factory's own material at its root: `Makefile`, `init`, `scripts/`, `skills/`,
`commands/`, `agents/` and `docs/` sit beside `apps/` and `project.json`, and every path the factory writes or
names assumes so. A repository the factory did not make already has a `Makefile`, a `docs/` and a root of its own,
and the method has to be installed *beside* those rather than over them. `project.json`'s `layout.delivery`
says where: `.` in every generated project — nothing moves and not one byte changes — and a directory such
as `delivery` where the material is wrapped around an existing codebase. (That path is experimental, as
`AGENTS.md` defines the word; this key is its first piece.)

Two things follow from a value other than `.`, and both are done here in one pass over the assembled files
rather than threaded through every part that names a path. The *delivery paths* — the seven roots above and
everything under them — are placed under the directory. And the text of every file that is run or read from
the repository's root is re-pointed: a root-relative `scripts/…`, `skills/…`, `commands/…`, `agents/…` or
`docs/…`, and `./init`, gain the prefix, exactly as `toolkit.spoken_for` respells `apps/service` on the way
in. The scripts themselves are left alone: code under `scripts/` finds the root by the nearest `project.json` and its
siblings by its own location, and a literal in it that reads `docs/…` relative to its own tree would be
broken by a prefix, not fixed. Not re-pointed either: a path already inside another (`apps/x/scripts/`, a
URL's `/docs/`), a relative `../docs/` — the trees move whole, so a link inside one stays right — and the
word `Makefile`, which has no runtime meaning in prose. Where a recipe or a workflow has to reach the
Makefile it says `make -f <delivery>/Makefile`, which is `Layout.make`.

`applications` and `packages` are recorded beside `delivery` and are still the constants `apps` and
`packages` everywhere; `scripts/deploy.py` reads the second, and nothing yet reads the first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import GenerationError

# What moves under `layout.delivery`: these paths, and everything below the directories among them.
DELIVERY_ROOTS = ("Makefile", "init", "scripts", "skills", "commands", "agents", "docs")
# Files whose text is *not* re-pointed: code that finds its own way (see the module docstring).
CODE = "scripts/"
# A root-relative pointer to a delivery directory — not already inside a path, a URL or a relative climb.
POINTER = re.compile(r"(?<![\w/.@-])(scripts|skills|commands|agents|docs)/")
INIT = re.compile(r"(?<![\w/.-])\./init(?![\w-])")
SEGMENT = re.compile(r"[\w.-]+")


def is_delivery(path: str) -> bool:
    """Whether `path`, as the factory assembles it for a root layout, is the factory's delivery material."""
    return any(path == root or path.startswith(f"{root}/") for root in DELIVERY_ROOTS)


@dataclass(frozen=True)
class Layout:
    """`project.json`'s `layout`, as far as anything reads it: where the delivery material lives."""

    delivery: str = "."

    @property
    def moved(self) -> bool:
        return self.delivery != "."

    @property
    def make_flag(self) -> str:
        """What `make` — or a recipe's `$(MAKE)`, which does not pass `-f` down — needs to find the Makefile."""
        return f" -f {self.delivery}/Makefile" if self.moved else ""

    @property
    def make(self) -> str:
        """How a workflow invokes this project's Makefile from the repository root."""
        return f"make{self.make_flag}"

    @property
    def to_root(self) -> str:
        """The relative path from the delivery directory back up to the repository root."""
        return "/".join(".." for _ in self.delivery.split("/")) if self.moved else "."

    def record(self) -> dict[str, str]:
        return {"delivery": self.delivery}

    def under(self, path: str) -> str:
        """A path of the factory's that is not one of the six delivery roots, put under the delivery directory."""
        return f"{self.delivery}/{path}" if self.moved else path

    def place(self, path: str) -> str:
        """Where a file the factory assembled at `path` lands in this layout."""
        return f"{self.delivery}/{path}" if self.moved and is_delivery(path) else path

    def repoint(self, path: str, text: str) -> str:
        """`text`, the content of the file at `path`, with its root-relative pointers spelled for this layout."""
        if not self.moved or path.startswith(CODE):
            return text
        return INIT.sub(f"./{self.delivery}/init", POINTER.sub(rf"{self.delivery}/\1/", text))

    def relocate(self, files: dict[str, str], protected: tuple[str, ...] = ()) -> dict[str, str]:
        """The assembled files, placed and re-pointed for this layout. The same mapping under `.`.

        `protected` are strings that are somebody's words and not the factory's pointers — a recorded command, a
        row's evidence, a quick win's `where` — which `repoint` must leave exactly as they were wherever they appear:
        the third real adoption recorded `python3 scripts/check-secrets.py`, the repository's own script, and every
        page, the Makefile and `project.json` itself came out naming `delivery/scripts/check-secrets.py`, which the
        gate then ran and could not find.
        """
        if not self.moved:
            return files
        kept = [word for word in dict.fromkeys(protected) if word and POINTER.search(word)]
        placeholders = {word: f"\x00{index}\x00" for index, word in enumerate(kept)}

        def shield(text: str) -> str:
            for word, placeholder in placeholders.items():
                text = text.replace(word, placeholder)
            return text

        def restore(text: str) -> str:
            for word, placeholder in placeholders.items():
                text = text.replace(placeholder, word)
            return text

        return {self.place(path): restore(self.repoint(path, shield(text))) for path, text in files.items()}


def layout_of(document: dict) -> Layout:
    """The layout a written `project.json` records — `.` where it records none, as every manifest written
    before this key did — refusing a value that is not a relative directory inside the repository."""
    layout = document.get("layout")
    delivery = layout.get("delivery", ".") if isinstance(layout, dict) else "."
    if delivery == ".":
        return Layout()
    segments = delivery.split("/") if isinstance(delivery, str) else []
    if not segments or not all(SEGMENT.fullmatch(part) and part not in (".", "..") for part in segments):
        raise GenerationError(
            f"project.json records layout.delivery as {delivery!r}, which is not a relative directory inside "
            "this repository — `.` for the root, or a path such as `delivery`"
        )
    return Layout(delivery)


# Every generated project's layout, and the default wherever a part takes one.
AT_ROOT = Layout()
