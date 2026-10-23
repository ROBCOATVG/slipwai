"""`slipwai install` hands each name to its own kind's verb, by what the index says the name is.

A language package's CI installs its siblings with this one verb, and a sibling can be a target: it was refused
as `aws is a target, not a language`, which left the TypeScript package's CI reaching for a pinned source checkout
to get the clouds it is proved against.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_install
from slipwai.language_index import Unreachable


def index(**kinds: str) -> SimpleNamespace:
    return SimpleNamespace(releases={name: [SimpleNamespace(kind=kind)] for name, kind in kinds.items()})


class DispatchTest(unittest.TestCase):
    def run_install(self, argv: list[str], listed: SimpleNamespace | None) -> tuple[mock.Mock, mock.Mock]:
        reading = mock.patch.object(cli_install, "read_index",
                                    side_effect=Unreachable("file:///nowhere", "no index") if listed is None else None,
                                    return_value=listed)
        with reading, mock.patch.object(cli_install, "target_main") as target, \
                mock.patch.object(cli_install, "language_main") as language:
            cli_install.install_main(argv)
        return target, language

    def test_a_target_goes_to_target_install_and_a_language_to_language_install(self) -> None:
        target, language = self.run_install(["aws", "typescript"], index(aws="target", typescript="language"))
        target.assert_called_once_with(["install", "aws"])
        language.assert_called_once_with(["install", "typescript"])

    def test_targets_alone_ask_the_language_verb_nothing(self) -> None:
        target, language = self.run_install(["aws", "azure"], index(aws="target", azure="target"))
        target.assert_called_once_with(["install", "aws", "azure"])
        language.assert_not_called()

    def test_the_publisher_flag_goes_only_where_it_is_understood(self) -> None:
        target, language = self.run_install(["aws", "go", "--accept-publisher"], index(aws="target", go="language"))
        target.assert_called_once_with(["install", "aws", "--accept-publisher"])
        language.assert_called_once_with(["install", "go"])

    def test_with_no_index_to_ask_every_name_meets_the_language_verb(self) -> None:
        """Which then says what it says about an index it cannot reach, rather than this guessing a kind."""
        target, language = self.run_install(["aws"], None)
        target.assert_not_called()
        language.assert_called_once_with(["install", "aws"])


if __name__ == "__main__":
    unittest.main()
