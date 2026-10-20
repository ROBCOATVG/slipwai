"""The hook points: a closed set the keel owns, and the registry resolved from what is elected.

Version 1's extension did three things at three moments and each was a convention rather than a
declaration. The cost showed in `codegraph`, which wanted to sync after every delegate and could only get
there through one harness's own hooks — so it worked on Claude Code and silently did nothing anywhere else.
A convention is a thing each extension rediscovers and each harness breaks differently.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import hooks


class PointTest(unittest.TestCase):
    def test_the_three_version_1_had_are_still_here_and_say_what_they_were(self) -> None:
        for name in ("init", "project", "check"):
            with self.subTest(point=name):
                self.assertNotEqual(hooks.point(name).was, "nothing")

    def test_the_four_the_loop_adds_say_version_1_had_nothing(self) -> None:
        for name in ("before-stage", "after-stage", "boundary", "before-merge"):
            with self.subTest(point=name):
                self.assertEqual(hooks.point(name).was, "nothing")

    def test_the_compaction_pair_name_the_runner_verbs_they_replace(self) -> None:
        """`before-compact` and `after-compact` are not new behaviour: they are `cruise.py compacting` and
        `cruise.py resume`, which the keel wrote straight into `.claude/settings.json` and which therefore
        existed on one harness. A point says where it came from so that reading the set tells you what was
        moved and what was invented."""
        self.assertIn("cruise.py", hooks.point("before-compact").was)
        self.assertIn("cruise.py", hooks.point("after-compact").was)
        self.assertEqual(hooks.point("after-merge").was, "nothing")

    def test_before_merge_has_a_partner_now(self) -> None:
        """A gate that passed on a rebased branch is not the same event as a slice being on trunk — the
        merge can still be refused after it. An extension with something to do once the commit exists had
        no point to say so at, and `before-merge` was the nearest wrong answer."""
        self.assertIn("after-merge", hooks.NAMES)
        self.assertIn("commit", hooks.point("after-merge").given)

    def test_every_point_says_when_it_fires_and_what_it_hands_over(self) -> None:
        for declared in hooks.POINTS:
            with self.subTest(point=declared.name):
                self.assertTrue(declared.when)
                self.assertTrue(declared.given)

    def test_a_point_the_keel_has_not_got_is_refused_and_the_set_is_listed(self) -> None:
        """An extension declaring one would have its hook silently never run, which is the failure that is
        hardest to notice: installed, valid, and nothing happens, for ever."""
        with self.assertRaises(KeyError) as refused:
            hooks.point("before-search")
        self.assertIn("it does not add one", str(refused.exception))
        self.assertIn("before-merge", str(refused.exception))


class DeclarationTest(unittest.TestCase):
    def test_a_path_is_the_short_form_and_reads_the_same_as_the_long_one(self) -> None:
        """Most hooks are "run this here", and a manifest making each one an object would be punctuation."""
        short = hooks.declared({"hooks": {"check": "hooks/check.py"}})
        long = hooks.declared({"hooks": {"check": {"run": "hooks/check.py"}}})
        self.assertEqual(short["check"]["run"], long["check"]["run"])
        self.assertEqual(short["check"]["budget"], hooks.budget_of("check"))

    def test_a_check_hook_has_the_minutes_a_gate_takes(self) -> None:
        """hr-test-2: ux-gates' render gates took minutes and 30 seconds ended them every time."""
        declared = hooks.declared({"hooks": {"check": "hooks/check.py", "after-stage": "sync.py"}})
        self.assertEqual(declared["check"]["budget"], "600s")
        self.assertEqual(declared["after-stage"]["budget"], hooks.DEFAULT_BUDGET)

    def test_a_declared_budget_wins_over_the_default(self) -> None:
        declared = hooks.declared({"hooks": {"after-stage": {"run": "sync.py", "budget": "90s"}}})
        self.assertEqual(declared["after-stage"]["budget"], "90s")

    def test_a_hook_naming_no_script_is_refused(self) -> None:
        with self.assertRaises(ValueError) as refused:
            hooks.declared({"hooks": {"check": {}}})
        self.assertIn("names no script to run", str(refused.exception))

    def test_a_manifest_declaring_an_unknown_point_is_refused(self) -> None:
        with self.assertRaises(KeyError):
            hooks.declared({"hooks": {"whenever": "x.py"}})

    def test_a_manifest_with_no_hooks_block_still_declares_the_two_with_defaults(self) -> None:
        """Every extension installs and every extension tells the agent it is there, so those two points
        need no manifest line — which is what 6.1e replaced the convention with. A manifest naming neither
        is attached to both, through the registry, running the one file an extension is guaranteed to have."""
        self.assertEqual(
            hooks.declared({"name": "codegraph"}),
            {"init": {"run": "init.py", "budget": hooks.DEFAULT_BUDGET},
             "project": {"run": "init.py", "budget": hooks.DEFAULT_BUDGET}},
        )

    def test_a_manifest_naming_its_own_script_at_either_is_obeyed(self) -> None:
        """The whole of what was wrong before: a declaration that was read and then ignored."""
        declared = hooks.declared({"hooks": {"project": "hooks/reproject.py"}})
        self.assertEqual(declared["project"]["run"], "hooks/reproject.py")
        self.assertEqual(declared["init"]["run"], "init.py")


class RegistryTest(unittest.TestCase):
    def registry(self) -> dict:
        return hooks.registry({
            "uipro": {"hooks": {"check": "hooks/check.py"}},
            "codegraph": {"hooks": {"check": "hooks/check.py",
                                    "after-stage": {"run": "hooks/sync.py", "stages": ["implement"]}}},
        })

    def test_the_points_are_in_firing_order_not_in_manifest_order(self) -> None:
        self.assertEqual(list(self.registry()["points"]),
                         [name for name in hooks.NAMES if name in self.registry()["points"]])

    def test_several_extensions_on_one_point_are_in_name_order(self) -> None:
        """They run independently, so one failing does not stop the next — and the order is written down
        rather than being whatever the manifests happened to be read in."""
        on_check = self.registry()["points"]["check"]
        self.assertEqual([entry["extension"] for entry in on_check], ["codegraph", "uipro"])

    def test_a_point_nothing_attaches_to_is_left_out(self) -> None:
        self.assertNotIn("boundary", self.registry()["points"])

    def test_every_entry_carries_a_budget_so_a_hook_can_always_be_ended(self) -> None:
        for entries in self.registry()["points"].values():
            for entry in entries:
                with self.subTest(extension=entry["extension"]):
                    self.assertTrue(entry["budget"])

    def test_the_registry_is_a_controlled_file(self) -> None:
        """So a run cannot register a hook on itself."""
        self.assertTrue(hooks.REGISTRY.startswith(".slipwai/"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
