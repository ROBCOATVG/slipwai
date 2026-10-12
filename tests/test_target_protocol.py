"""The target protocol: what a `TARGET` object answers, and what the keel refuses when it does not.

The executable half of a target package. `target.json` is the declaration a catalog row is made from; this
is the part that has to be imported — the stacks, the scripts, the docs page, the preflight tools, the
image registry and the pipeline's sign-in — and it is declared here as the backend protocol is declared in
`registry.py`, so a page and a check cannot drift from each other.

**Required means required of a *managed* target.** A target the keel does not provision — the shape
`existing` has, where a project deploys somewhere the keel does not own — answers none of it, and holding
it to the stacks it has no business shipping would make the one honest unmanaged row impossible.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import target_protocol
from slipwai.target_protocol import SHAPES, Target, faults

ANSWERS = {
    target_protocol.SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
    target_protocol.SCRIPTS: {"scripts/deploy.py": "scripts/deploy.py"},
    target_protocol.TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org"),),
    target_protocol.IMAGE_REGISTRY: {"push": "cumulus image push"},
    target_protocol.DEPLOY_STEPS: lambda environment: f"  - run: make deploy ENV={environment}\n",
    target_protocol.DOCS_PAGES: {"docs/deployment.md": lambda selection: "# Where this goes\n"},
}


def target(changes: dict | None = None) -> Target:
    """A whole target with those members changed; a member set to None is one it does not answer."""
    answers = {**ANSWERS, **(changes or {})}
    return Target(name="cumulus", answers={k: v for k, v in answers.items() if v is not None})


class ProtocolTest(unittest.TestCase):
    def test_every_member_the_protocol_declares_has_a_name_a_kind_and_a_shape(self) -> None:
        for member in target_protocol.PROTOCOL:
            with self.subTest(member=member.name):
                self.assertTrue(member.name and member.shape)
                self.assertIsNotNone(member.kind)

    def test_no_member_is_declared_twice(self) -> None:
        names = [member.name for member in target_protocol.PROTOCOL]
        self.assertEqual(sorted(names), sorted(set(names)))

    def test_both_shapes_are_named_where_the_protocol_can_be_read(self) -> None:
        """A managed target has two stacks and always has: the account's, written once, and the service's,
        applied per environment. The pair is declared, not left to each package to name."""
        self.assertEqual(target_protocol.BOTH_SHAPES, ("bootstrap", "service"))


class FaultsTest(unittest.TestCase):
    def test_a_whole_managed_target_has_no_faults(self) -> None:
        self.assertEqual(faults(target(), managed=True), [])

    def test_a_missing_required_member_is_named(self) -> None:
        found = faults(target({target_protocol.SHAPES: None}), managed=True)
        self.assertEqual(found, ["target cumulus is missing shapes"])

    def test_an_unmanaged_target_owes_none_of_it(self) -> None:
        self.assertEqual(faults(Target(name="elsewhere"), managed=False), [])

    def test_a_member_answered_with_the_wrong_kind_is_named_with_both_kinds(self) -> None:
        found = faults(target({target_protocol.TOOLS: "tofu"}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("tools", found[0])
        self.assertIn("str", found[0])
        self.assertIn("tuple", found[0])

    def test_a_key_that_is_not_a_member_is_refused_rather_than_ignored(self) -> None:
        one = Target(name="cumulus", answers={**ANSWERS, "shapes": {}})  # type: ignore[dict-item]
        found = faults(one, managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("not a protocol member", found[0])

    def test_a_shape_the_protocol_does_not_know_is_refused_naming_the_two(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": ("a.tf",), "service": ("b.tf",), "extra": ("c.tf",)}}),
                       managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("extra", found[0])

    def test_a_shape_left_out_is_refused_by_name(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": ("a.tf",)}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("service", found[0])

    def test_a_shape_with_no_files_in_it_is_a_stack_that_applies_nothing(self) -> None:
        found = faults(target({SHAPES: {"bootstrap": (), "service": ("b.tf",)}}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("bootstrap", found[0])

    def test_a_tool_that_does_not_say_why_and_where_is_refused(self) -> None:
        found = faults(target({target_protocol.TOOLS: (("tofu",),)}), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("where to get it", found[0])

    def test_the_name_a_target_gives_itself_is_held_to_what_a_name_may_be(self) -> None:
        found = faults(Target(name="Cumulus Cloud", answers=ANSWERS), managed=True)
        self.assertEqual(len(found), 1)
        self.assertIn("lower-case name", found[0])

    def test_every_fault_is_named_at_once_rather_than_the_first(self) -> None:
        one = Target(name="cumulus", answers={target_protocol.TOOLS: "tofu"})
        self.assertEqual(len(faults(one, managed=True)), len(target_protocol.required()))


if __name__ == "__main__":
    unittest.main()
