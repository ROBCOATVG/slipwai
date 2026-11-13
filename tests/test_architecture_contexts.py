"""The architecture page's bounded contexts name where each lives, and a service's purpose is said once.

game-club-manager's one service holds seven contexts, and the page printed the service's whole paragraph under
every one of them — seven copies, which is also what made its migration conflict.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project.guidance import architecture
from slipwai.selection import Selection
from slipwai.services import service_app

PURPOSE = "The backend: accounts, clubs and the library."
STATE = Selection({"write-model": "state", "persistence": "postgres"})


class ContextsTest(unittest.TestCase):
    def test_a_service_holding_several_contexts_says_its_purpose_once(self) -> None:
        apps = [service_app("club-service", "toy-plain", 3000, STATE, first=True, purpose=PURPOSE,
                            contexts=["accounts", "clubs", "library"])]
        page = architecture("standard", apps)
        self.assertEqual(page.count(PURPOSE), 1, "the services line says it; the contexts do not repeat it")
        for context in ("accounts", "clubs", "library"):
            self.assertIn(f"- `{context}` — `apps/club-service`\n", page + "\n")

    def test_a_service_holding_one_context_keeps_its_purpose_beside_it(self) -> None:
        apps = [service_app("orders", "toy-plain", 3000, STATE, first=True, purpose=PURPOSE,
                            contexts=["ordering"])]
        self.assertIn(f"- `ordering` — `apps/orders`: {PURPOSE}", architecture("standard", apps))


if __name__ == "__main__":
    unittest.main()
