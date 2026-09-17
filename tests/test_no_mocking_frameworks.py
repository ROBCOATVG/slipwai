"""No test the factory ships reaches for a mocking framework.

The house rule is in AGENTS.md, in `/drive`'s Implementation stage and in the `testing` and `finding-seams`
skills: a collaborator that has to be stood in for is a fake written in the test tree against the real
interface, never a framework that records a call sequence. A generated project's own tests are the first
thing an agent reads to learn what a test here looks like, so one framework mock in the skeleton teaches the
opposite of every page that forbids it.

Prose may name the frameworks — the skills that forbid them have to — so only files that are *code* and are
*tests* are read. Generated rather than scanned in `assets/`, because the asset a project receives depends
on its answers: this walks the combinations that bring the most test files with them.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from support import FactoryTestCase, backends_under_test

from slipwai.catalog import CATALOG, axis_default

# What each spelling is, so a failure says why it is refused rather than only that it matched.
FRAMEWORKS = {
    r"\bvi\.mock\b": "Vitest module mock",
    r"\bvi\.mocked\b": "Vitest module mock",
    r"\bjest\.mock\b": "Jest module mock",
    r"\bunittest\.mock\b": "Python unittest.mock",
    r"\bmock\.patch\b": "Python unittest.mock",
    r"(?i)\bmockito\b": "Mockito",
    r"\bgomock\b": "gomock",
    r"\bMagicMock\b": "Python unittest.mock",
}
MOCKING = {re.compile(pattern): name for pattern, name in FRAMEWORKS.items()}

# A test, by the naming every one of the supported toolchains uses to find one.
TEST_NAMES = (
    re.compile(r"\.test\.(ts|tsx|js|jsx|mts)$"),
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"[^/]+_test\.(py|go)$"),
    re.compile(r"[^/]*(Test|Tests|IT)\.java$"),
)
# Anything else under a `tests/` or `test/` directory that is code rather than prose — a shared contract
# suite (`tests/contract/event-store-contract.ts`) is not named like a test and is read by every test there.
CODE = {".ts", ".tsx", ".js", ".jsx", ".mts", ".py", ".go", ".java", ".kt"}


def is_test(relative: str) -> bool:
    if any(pattern.search(relative) for pattern in TEST_NAMES):
        return True
    parts = relative.split("/")
    return Path(relative).suffix in CODE and ("tests" in parts[:-1] or "test" in parts[:-1])


class NoMockingFrameworkTest(FactoryTestCase):
    def test_no_generated_test_file_reaches_for_a_mocking_framework(self) -> None:
        offences: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                for profile in CATALOG["profiles"]:
                    for frontend in CATALOG["frontends"]:
                        # As many axes answered as the profile and the frontend allow, so every
                        # adapter's suite and the browser app's sign-in tests are present in at least
                        # one of the trees this walks. The standard profile has no event store to
                        # answer for, and customer sign-in needs a browser app to sign in from.
                        repo = self.generate(
                            directory,
                            f"mocks-{profile}-{backend}-{frontend}",
                            profile,
                            backend,
                            frontend,
                            event_store="postgres" if profile == "event-modelling" else "memory",
                            http=axis_default("http", backend, "none"),
                            auth="keycloak",
                            users="keycloak" if frontend != "none" else "none",
                        )
                        for path in sorted(repo.rglob("*")):
                            if not path.is_file() or "/.git/" in path.as_posix():
                                continue
                            relative = path.relative_to(repo).as_posix()
                            if not is_test(relative):
                                continue
                            try:
                                text = path.read_text()
                            except (UnicodeDecodeError, OSError):
                                continue
                            for pattern, name in MOCKING.items():
                                if pattern.search(text):
                                    offences.append(f"{repo.name}: {relative} uses {name} ({pattern.pattern})")
        self.assertEqual(
            [],
            sorted(set(offences)),
            "a generated test uses a mocking framework; write a fake at a seam instead "
            "(skills/testing, skills/finding-seams):\n  " + "\n  ".join(sorted(set(offences))),
        )

    def test_the_rule_would_notice_a_mock_reintroduced(self) -> None:
        """The scan itself, held to a file it must catch and two it must not."""
        self.assertTrue(is_test("apps/web/tests/auth/Account.test.tsx"))
        self.assertTrue(is_test("scripts/test_benchmark.py"))
        self.assertTrue(is_test("apps/service/tests/contract/event-store-contract.ts"))
        self.assertTrue(is_test("apps/service/src/test/java/com/example/HealthTest.java"))
        self.assertFalse(is_test("skills/finding-seams/SKILL.md"))
        self.assertFalse(is_test("apps/service/src/events.ts"))
        matched = [name for pattern, name in MOCKING.items() if pattern.search("vi.mock('react-oidc-context')")]
        self.assertEqual(["Vitest module mock"], matched)
