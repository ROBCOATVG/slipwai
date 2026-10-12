"""One command-to-skill spelling for project projection and standalone harness material."""
from __future__ import annotations

import json

STAMP = "Generated from {source}. Edit the canonical file and rerun ./init."


def parse_text(source: str, name: str) -> tuple[str, str, str]:
    description = f"Run the {name} project workflow"
    argument_hint = ""
    body = source
    if source.startswith("---\n"):
        end = source.find("\n---\n", 4)
        if end != -1:
            header = source[4:end]
            body = source[end + 5 :].lstrip("\n")
            for line in header.splitlines():
                key, separator, value = line.partition(":")
                if not separator:
                    continue
                if key == "description":
                    description = value.strip().strip('"')
                elif key == "argument-hint":
                    argument_hint = value.strip().strip('"')
    return description, argument_hint, body



def command_as_skill(name: str, description: str, hint: str, body: str, source: str) -> str:
    arguments = f"\n**Arguments:** {hint}\n" if hint else ""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"<!-- {STAMP.format(source=source)} -->\n"
        f"{arguments}\n{body}"
    )

