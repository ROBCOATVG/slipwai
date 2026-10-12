"""The keel names no place a project is deployed to — and the seven lines where a cloud's name is a word.

10.6 made it a gate that the keel cannot *import* a target package. This is the other half, which an import
rule cannot reach: a dict keyed by `"aws"`, a docstring whose example is Cognito, a comment about what
Fargate runs. None of those imports anything, and every one of them is the keel knowing a product.

**A gate rather than a grep somebody remembers to run.** The plan's mark for 10.5 is that `grep -ri aws
src/slipwai` finds nothing but a comment saying there is nothing, and a mark nothing enforces is a mark that
holds until the next person writes an example. So the search is here, and the only way past it is to add a
line to `ALLOWED` with a reason, which is a thing a reviewer sees.

**What is allowed, and why there is anything at all.** Eight lines name a cloud, and in none of them is the
cloud a place this keel deploys to:

- a CI system or an infrastructure file that happens to be a cloud vendor's, read off a brownfield
  repository or offered in a prompt;
- the format of an access key, in a scanner that looks for leaked secrets — `AKIA…` *is* an AWS access key,
  and a scanner that called it something else would be a scanner that lied about what it found;
- a word people say about hosting, in the matcher that notices they are talking about it;
- a JDK distribution's image name, which is a build input and not a destination.

Each of those would be made worse by taking the name out, which is the test of whether a mention is a
mention. The rest went in 10.3, 10.4 and 10.5.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

KEEL = Path(__file__).resolve().parents[1] / "src/slipwai"
#: Every product name that would mean the keel knew a place. `aws` and `ecr` are word-bounded because
#: `draws` and `specs` are ordinary English and this file is not about them.
NAMES = re.compile(
    r"\baws\b|awstemplate|\bazure\b|amazon|cognito|fargate|cloudfront|\bentra\b|\becr\b|\bacr\b|"
    r"\brds\b|\bflexible-server\b",
    re.IGNORECASE,
)

#: Module → the lines in it a cloud's name may appear on, each with why it is not the keel knowing a place.
#: A fragment rather than a line number, so the list does not rot the first time somebody adds an import.
ALLOWED: dict[str, list[tuple[str, str]]] = {
    "targets.py": [
        ("No module in `src/slipwai/` names a cloud",
         "the comment the plan's own mark asks for: `grep -ri aws src/slipwai` finds this and nothing else "
         "that is about a place, and it says where the rule is kept"),
        ("here, no `azure`, no Cognito and no Fargate",
         "the second line of that same comment, which has to name them to be worth greping for"),
    ],
    "survey.py": [
        ("azure-pipelines.yml", "a CI configuration file this keel looks for in a repository it is adopting"),
        ("AWSTemplateFormatVersion", "the line that tells a CloudFormation template from any other YAML, in "
                                     "the survey of a repository the method is being installed around. What "
                                     "that repository already has is not where this keel deploys anything"),
    ],
    "delivery_facts.py": [
        ("azure-pipelines.yml", "the same file, in the table that says which CI a repository already has"),
        ("dev.azure.com", "the host that says the same thing when the file is not in the repository"),
    ],
    "cli_interview.py": [
        ("Jenkins, Azure, Bitbucket, CircleCI", "the CI systems the interview offers, named so a person "
                                                "recognises theirs; nothing is written for any of them"),
    ],
    "quick_wins.py": [
        ("AWS access key", "the format of a leaked secret. `AKIA…` is an AWS access key, and a scanner that "
                           "called it anything else would be one that lied about what it found"),
    ],
    "strategy.py": [
        ("move to (aws|azure|gcp|the cloud)", "words people say about hosting, in the matcher that notices "
                                              "they are saying them"),
    ],
    "platform.py": [
        ("amazoncorretto", "a JDK distribution's image name: a build input, not a destination"),
    ],
}


def modules() -> list[Path]:
    return sorted(path for path in KEEL.rglob("*.py"))


def allowed(path: Path, line: str) -> bool:
    name = str(path.relative_to(KEEL))
    return any(fragment in line for fragment, _why in ALLOWED.get(name, []))


class NoCloudTest(unittest.TestCase):
    def test_no_keel_module_names_a_place_a_project_is_deployed_to(self) -> None:
        found = [f"{path.relative_to(KEEL)}:{number}: {line.strip()}"
                 for path in modules()
                 for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if NAMES.search(line) and not allowed(path, line)]
        self.assertEqual(found, [], "\n".join([
            "the keel names a place a project is deployed to. Every place is a package: ask the target for "
            "it (`loaded_targets.answer`), or say it in words that are not a product's.",
            "If the name genuinely is not a destination — a CI system, a secret's format, a build input — "
            "add it to ALLOWED in this file with the reason.",
            *found,
        ]))

    def test_every_allowed_line_is_still_there(self) -> None:
        """An allowance for a line nobody has is an allowance nobody can argue with. It goes when it does."""
        for name, rows in ALLOWED.items():
            text = (KEEL / name).read_text(encoding="utf-8")
            for fragment, _why in rows:
                with self.subTest(module=name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_every_allowance_says_why(self) -> None:
        for name, rows in ALLOWED.items():
            for fragment, why in rows:
                with self.subTest(module=name, fragment=fragment):
                    self.assertGreater(len(why), 30, f"{name}: {fragment} is allowed without a reason")

    def test_the_keel_says_where_the_rule_is(self) -> None:
        """The mark the plan sets for 10.5 is that a grep finds a comment about there being nothing, so
        there is one, and it points at this file."""
        said = (KEEL / "targets.py").read_text(encoding="utf-8")
        self.assertIn("tests/test_no_cloud_named.py", said)


if __name__ == "__main__":
    unittest.main()
