"""The two identity axes are internal and external, and the stacks moved their state rather than losing it.

`Staff` and `Customer` were a guess about who uses the product. Internal and external say the thing that
actually differs — which side of the organisation an account is on.

The half of this that matters is the terraform. **A resource address is state, not a name.** Renaming a
user pool from `.staff` to `.internal` is, to terraform, one resource destroyed and another created,
which for a user pool is every account in it gone on the next apply. Every renamed address carries a `moved`
block, and this is the suite that says so — because the failure it prevents is silent until somebody runs
`tofu apply` against production.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: This package's own service stack, and the number of addresses it renamed. A number rather than a
#: diff, because a diff is only true of the commit that made it.
STACKS = (ROOT / "service",)
RESOURCE = re.compile(r'^resource\s+"(\w+)"\s+"(\w+)"', re.M)
MOVED = re.compile(r"moved\s*\{\s*from\s*=\s*([\w.\[\]\"-]+)\s*to\s*=\s*([\w.\[\]\"-]+)\s*\}")
#: Everything a stack declares a name for. Checked instead of the whole text, because the prose that
#: explains the rename says the old words on purpose and so do the `moved` blocks.
DECLARED = re.compile(r'^(?:resource\s+"\w+"|variable|output|module|data\s+"\w+")\s+"(\w+)"', re.M)
LOCAL = re.compile(r"^\s{2}(\w+)\s*=", re.M)
MOVES = 16


def stack_text(place: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(place.glob("*.tf")))


class WordTest(unittest.TestCase):
    def test_nothing_either_stack_declares_is_named_staff_or_customer(self) -> None:
        """The names, not the prose. A `moved` block says `staff` on purpose — that is the whole of what it
        is for — and the comment above it explains why the rename needed one."""
        for place in STACKS:
            text = stack_text(place)
            for name in sorted(set(DECLARED.findall(text)) | set(LOCAL.findall(text))):
                with self.subTest(stack=place.name, name=name):
                    self.assertNotIn("staff", name.lower())
                    self.assertNotIn("customer", name.lower())

    def test_the_interview_asks_internal_and_external(self) -> None:
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["axes"]["auth"]["prompt"], "Internal authentication")
        self.assertEqual(catalog["axes"]["users"]["prompt"], "External authentication")

    def test_the_axis_keys_did_not_move(self) -> None:
        """A key is read by a generated project and by every `project.json` already written. Renaming the
        words is a rename; renaming these would be a migration, and nothing here needed one."""
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        self.assertIn("auth", catalog["axes"])
        self.assertIn("users", catalog["axes"])


class MovedTest(unittest.TestCase):
    """Every address that was renamed has a `moved` block, and every block points at a resource that exists.

    Read against `git show HEAD~` would be a test of one commit. Read against the blocks themselves, this
    keeps being true: a block whose `to` names nothing is a block that silently does nothing, which is the
    same outcome as never having written it.
    """

    def blocks(self, place: Path) -> list[tuple[str, str]]:
        return MOVED.findall(stack_text(place))

    def test_every_moved_block_points_at_a_resource_that_exists(self) -> None:
        for place in STACKS:
            addresses = {f"{kind}.{name}" for kind, name in RESOURCE.findall(stack_text(place))}
            for was, now in self.blocks(place):
                with self.subTest(stack=place.name, moved=f"{was} -> {now}"):
                    self.assertIn(now, addresses, f"{now} is not a resource in {place}")

    def test_no_moved_block_points_at_an_address_that_still_exists(self) -> None:
        """A `from` that is still declared is a duplicate, and terraform refuses the plan."""
        for place in STACKS:
            addresses = {f"{kind}.{name}" for kind, name in RESOURCE.findall(stack_text(place))}
            for was, _now in self.blocks(place):
                with self.subTest(stack=place.name, was=was):
                    self.assertNotIn(was, addresses)

    def test_every_renamed_address_is_accounted_for(self) -> None:
        """The count that matters: each stack renamed this many addresses, and each has its block. A number
        rather than a diff, because a diff is only true of the commit that made it."""
        for place, owed in zip(STACKS, (MOVES,), strict=True):
            with self.subTest(stack=place.name):
                self.assertEqual(len(self.blocks(place)), owed)


if __name__ == "__main__":
    unittest.main()
