"""What a captain lets be read, and what its own session may do (whole-branch review, round 2).

A captain may allow a slice's session one read outside its berth, and its own session reads its brief, its
events and the deck. Both are decided on the resolved path: a link is what it leads to, a relative path is the
berth's, case is no disguise, and the project's keys, environment files, `.slipwai/` and `.git/` are read by
nobody through a captain. The captain session's policy decides on the whole request — what the session's
updates already said of a tool call, a command wherever it is, the fields beside it — and counts a shape it does
not expect with its keys named.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import checkout_packages  # noqa: F401
from test_captain_helm import HelmBase, loaded

OPTIONS = [{"optionId": "y", "kind": "allow_once"}, {"optionId": "n", "kind": "reject_once"}]


class SliceReadTest(HelmBase):
    """M-A: `captain_events.unreadable`, what a captain's `allow` can hand a slice."""

    def setUp(self) -> None:
        super().setUp()
        self.project = self.root.resolve()
        self.berth = Path(tempfile.mkdtemp()).resolve()
        self.outside = Path(tempfile.mkdtemp()).resolve()
        for folder in (self.project / ".slipwai/run/talk", self.project / ".slipwai/run/orders/ORD",
                       self.project / ".git", self.project / "docs"):
            folder.mkdir(parents=True, exist_ok=True)
        (self.project / ".slipwai/run/talk/.key").write_text("K" * 64, encoding="utf-8")
        (self.project / ".slipwai/run/orders/ORD/x.json").write_text("{}", encoding="utf-8")
        for name in (".env", ".env.local", "deploy.pem", "id_ed25519", ".git/config", "docs/README.md"):
            (self.project / name).write_text("x", encoding="utf-8")
        (self.outside / "secret").write_text("s", encoding="utf-8")
        (self.berth / "notes.md").write_text("n", encoding="utf-8")
        os.symlink(self.outside / "secret", self.project / "link-out")
        os.symlink(self.project / ".slipwai/run/talk/.key", self.project / "notes.txt")
        self.events = loaded(self.root, "captain_events")

    def why(self, kind: str, *places: str) -> str:
        return self.events.unreadable({"tool": {"kind": kind, "locations": list(places)}, "root": str(self.berth)},
                                      self.project)

    def test_one_plain_file_of_the_project_is_allowed_and_nothing_else(self) -> None:
        self.assertEqual(self.why("read", str(self.project / "docs/README.md")), "")
        readme = str(self.project / "docs/README.md")
        self.assertTrue(self.events.readable({"tool": {"kind": "read", "locations": [readme]}, "root": str(self.berth)},
                                             self.project))
        refused = {
            ".env": ("read", str(self.project / ".env")), ".env.local": ("read", str(self.project / ".env.local")),
            "a pem": ("read", str(self.project / "deploy.pem")),
            "a private key": ("read", str(self.project / "id_ed25519")),
            ".git/config": ("read", str(self.project / ".git/config")),
            "the key": ("read", str(self.project / ".slipwai/run/talk/.key")),
            "the key as .KEY": ("read", str(self.project / ".slipwai/run/talk/.KEY")),
            "the key behind an innocent link": ("read", str(self.project / "notes.txt")),
            "the run's orders": ("read", str(self.project / ".slipwai/run/orders/ORD/x.json")),
            "a link out of the project": ("read", str(self.project / "link-out")),
            "out by ..": ("read", f"{self.project}/../{self.outside.name}/secret"),
            "outside": ("read", "/etc/hosts"), "a home key": ("read", "~/.ssh/id_rsa"),
            "a relative path, the berth's": ("read", "notes.md"),
            "a folder": ("read", str(self.project / "docs")), "nothing there": ("read", str(self.project / "nope.md")),
            "a NUL": ("read", f"{self.project}/a\x00b"),
            "a search of the project": ("search", str(self.project)),
            "a search of the conversations": ("search", str(self.project / ".slipwai/run/talk")),
            "a fetch": ("fetch", str(self.project / "docs/README.md")),
            "a think": ("think", str(self.project / "docs/README.md")),
            "an edit": ("edit", str(self.project / "docs/README.md")),
        }
        for name, (kind, place) in refused.items():
            with self.subTest(name=name):
                self.assertNotEqual(self.why(kind, place), "", place)
        self.assertNotEqual(self.why("read"), "", "no location")
        self.assertNotEqual(self.why("read", str(self.project / "docs/README.md"), "/etc/hosts"), "", "two")

    def test_the_rule_s_refusal_says_the_true_reason(self) -> None:
        self.assertIn("secret by its name", self.why("read", str(self.project / ".slipwai/run/talk/.KEY")))
        # A file that exists on every platform and is no part of the project: `/etc/hosts` is not on Windows.
        self.assertIn("outside the project", self.why("read", str(Path(__file__).resolve())))
        self.assertIn("under .slipwai/", self.why("read", str(self.project / ".slipwai/run/orders/ORD/x.json")))
        self.assertIn("only a read", self.why("edit", str(self.project / "docs/README.md")))


class OwnSessionTest(HelmBase):
    """M-A for the captain's own reads, and M-D: the session's policy on the whole request."""

    def setUp(self) -> None:
        super().setUp()
        self.agent = loaded(self.root, "captain_agent")
        self.agent.REFUSED.update(count=0, first="", why="", shapes=[])
        (self.root / "docs").mkdir()
        (self.root / "docs/README.md").write_text("x", encoding="utf-8")
        (self.root / ".env").write_text("x", encoding="utf-8")
        self.event = self.root / ".slipwai/events/ORD/e1.json"  # a project not yet migrated keeps its run here
        self.event.parent.mkdir(parents=True)
        self.event.write_text("{}", encoding="utf-8")
        self.command = f"{self.agent.order_command()} none --why 'x' --event e1"

    def permit(self, tool_call: object, options: object = OPTIONS) -> str | None:
        return self.agent.permit(tool_call, options)

    def test_it_reads_its_brief_events_and_the_project_and_nothing_secret_or_outside(self) -> None:
        for place in (str(self.root / "docs/README.md"), str(self.event)):
            with self.subTest(place=place):
                self.assertEqual(self.permit({"kind": "read", "locations": [{"path": place}]}), "y")
        for place in (str(self.root / ".env"), str(self.root / ".ENV"), "~/.ssh/id_rsa", "/etc/hosts",
                      str(self.root / ".slipwai/talk/.key")):
            with self.subTest(place=place):
                self.assertEqual(self.permit({"kind": "read", "locations": [{"path": place}]}), "n")
        self.assertEqual(self.permit({"kind": "read", "rawInput": {"file_path": str(self.root / ".env")}}), "n")
        self.assertEqual(self.permit({"kind": "read"}), "n", "a read that names no file")

    def test_a_command_is_judged_as_a_command_whatever_its_kind_says(self) -> None:
        for kind in ("think", "read", "search", None):
            with self.subTest(kind=kind):
                self.assertEqual(self.permit({"kind": kind, "rawInput": {"command": "rm -rf /"}}), "n")
        self.assertEqual(self.permit({"kind": "think"}), "y")

    def test_a_request_with_no_kind_carrying_the_order_command_is_an_execute_and_allowed(self) -> None:
        self.assertEqual(self.permit({"toolCallId": "c1", "rawInput": {"command": self.command}}), "y")

    def test_fields_beside_the_command_the_tokenizer_never_saw_refuse_it(self) -> None:
        self.assertEqual(self.permit({"kind": "execute", "rawInput": {"command": self.command, "cwd": str(self.root),
                                                                     "description": "x"}}), "y")
        for extra, rule in (({"env": {"PATH": "/tmp"}}, "an environment of its own"),
                            ({"args": ["; rm -rf /"]}, "words beside its command line"),
                            ({"cwd": "/tmp"}, "a folder outside the project")):
            with self.subTest(extra=extra):
                call = {"kind": "execute", "rawInput": {"command": self.command, **extra}}
                self.assertEqual(self.permit(call), "n")
                self.assertIn(rule, self.agent.refusal(call))

    def test_an_unexpected_shape_is_refused_and_counted_by_its_keys_alone(self) -> None:
        self.assertIsNone(self.permit(None, None))
        self.assertEqual(self.permit({"kind": "fetch", "rawInput": {"url": "https://example.com/secret-value"}}), "n")
        self.assertEqual(self.permit({"kind": "execute", "rawInput": "rm -rf /"}), "n")
        self.assertEqual(self.permit({"kind": "execute", "rawInput": {"command": f"{sys.executable} a\x00b x"}}), "n")
        said = self.agent.Runner("ORD", self.run_dir, self.agent.settings({}), (["x"], None)).refusals()
        self.assertIn("refused 4 commands", said)
        self.assertIn("kind fetch; keys kind, rawInput; rawInput keys url", said)
        self.assertNotIn("secret-value", said, "keys, never values")


class MergedCallTest(HelmBase):
    """M-D (i): a permission asked of a tool call is decided on what its updates already said of it."""

    def test_a_permission_that_omits_kind_and_input_is_decided_on_the_tool_call_s_updates(self) -> None:
        acp = loaded(self.root, "acp")
        session = acp.Session(["true"], self.root, lambda update: None, lambda call, options: None,
                              lambda params: ("decline", None))
        session.known({"sessionUpdate": "tool_call", "toolCallId": "c1", "kind": "execute", "title": "run",
                       "rawInput": {"command": "x"}})
        session.known({"sessionUpdate": "tool_call_update", "toolCallId": "c1", "status": "pending"})
        self.assertEqual(session.whole({"toolCallId": "c1", "title": "Run it"}),
                         {"toolCallId": "c1", "kind": "execute", "title": "Run it", "rawInput": {"command": "x"},
                          "status": "pending"})
        self.assertEqual(session.whole({"toolCallId": "c2"}), {"toolCallId": "c2"})


class TokensTest(HelmBase):
    """L1 and L5: what the tokenizer refuses outside quotes, each pinned."""

    def test_each_mark_a_shell_reads_as_more_than_words_is_refused_outside_quotes_and_a_letter_inside(self) -> None:
        agent = loaded(self.root, "captain_agent")
        for mark in ("(", ")", "*", "?", "[", "~", "{", "}"):
            with self.subTest(mark=mark):
                self.assertTrue(str(agent.tokens(f"x a{mark}b")).endswith("outside quotes"))
                self.assertEqual(agent.tokens(f"x 'a{mark}b'"), ["x", f"a{mark}b"])
        self.assertIn("begins with `=`", str(agent.tokens("x =ls")))
        self.assertEqual(agent.tokens("x a=b"), ["x", "a=b"])
        self.assertEqual(agent.tokens("x a\\\nb"), "a line continued outside quotes")
