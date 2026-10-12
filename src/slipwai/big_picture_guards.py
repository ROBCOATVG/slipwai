"""Literal role arguments and distinct route declarations for the survey's permission proposals.

Authorization expressions that need runtime evaluation remain questions. These helpers read literal
roles; they never collapse separate operations or services into a permission just because paths match.
"""
from __future__ import annotations

import re

GUARD = re.compile(
    r"(?:has(?:Any)?(?:Role|Authority)|(?:require|has|check|assert|ensure)(?:Any)?Roles?|"
    r"Roles|roles?_(?:required|accepted)|(?:require|authorize)_(?:role|as))\(([^)]*)\)"
)
LITERAL = re.compile(r"['\"]([A-Za-z][\w-]*(?:\s*,\s*[A-Za-z][\w-]*)*)['\"]")
DOTNET = re.compile(r'\[Authorize\s*\(\s*Roles\s*=\s*"([^"\n]+)"')
METHOD = re.compile(r"\.(get|post|put|patch|delete|all)\(|(?:@|\[)(Get|Post|Put|Patch|Delete|HttpGet|HttpPost|"
                    r"HttpPut|HttpPatch|HttpDelete)|\.Map(Get|Post|Put|Patch|Delete)\(", re.IGNORECASE)


def roles(lines: list[str], rules: tuple[re.Pattern[str], ...]) -> list[tuple[int, str, bool]]:
    """Literal roles with whether a guard grants them access; bare constants are evidence only."""
    found: dict[tuple[int, str], bool] = {}
    for number, line in enumerate(lines, start=1):
        names = [(match.group(1), rule not in rules[-2:]) for rule in rules for match in rule.finditer(line)]
        arguments = [match.group(1) for match in GUARD.finditer(line)]
        names += [(match.group(1), True) for args in arguments for match in LITERAL.finditer(args)]
        names += [(match.group(1), True) for args in arguments for rule in rules[-2:]
                  for match in rule.finditer(args)]
        names += [(match.group(1), True) for match in DOTNET.finditer(line)]
        for name, guarded in names:
            for part in name.split(','):
                pair = (number, part.strip().lower())
                found[pair] = found.get(pair, False) or guarded
    return [(number, name, guarded) for (number, name), guarded in found.items()]


def operation(path: str, number: int, route: str, lines: list[str]) -> str:
    """Keep method and source declaration identity: two applications may serve the same URL."""
    method = METHOD.search(lines[number - 1])
    verb = next((part for part in method.groups() if part), "") if method else ""
    verb = verb.upper().removeprefix("HTTP")
    return f"{verb + ' ' if verb else ''}{route} ({path}:{number})"
