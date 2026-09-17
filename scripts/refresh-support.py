#!/usr/bin/env python3
"""Refresh `assets/adoption/support.json` from endoflife.date, and date the snapshot.

    python3 scripts/refresh-support.py            # rewrite the table from the network
    python3 scripts/refresh-support.py --check    # say how old the snapshot is; exit 1 past 180 days

The table is what an adopted repository's survey dates its runtimes and frameworks against (`slipwai.platform`), so
that `survey/structure.md` can say "Spring Framework 3.2.8 left support on 2016-12-31" offline, at adopt time. It is
a snapshot and goes stale, which is why it carries its date and why this script exists: run it before a release, and
the cycles endoflife.date publishes for each product replace the ones here. A product with no `endoflife` slug —
JUnit, which endoflife.date does not track — is kept by hand and left as it is. Nothing here touches a project.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "assets/adoption/support.json"
API = "https://endoflife.date/api/{slug}.json"
STALE_AFTER = datetime.timedelta(days=180)


def cycles_of(slug: str) -> dict[str, dict]:
    with urllib.request.urlopen(API.format(slug=slug), timeout=30) as response:  # noqa: S310 — a fixed https host
        published = json.load(response)
    cycles: dict[str, dict] = {}
    for entry in published:
        cycle = str(entry.get("cycle", ""))
        eol = entry.get("eol")
        if not cycle:
            continue
        # endoflife.date writes `false` for "no end of life announced" and a date otherwise; a `true` means gone
        # already, with no date to give — recorded as the day before this snapshot so it reads as out of support.
        if eol is False:
            cycles[cycle] = {"eol": None}
        elif eol is True:
            cycles[cycle] = {"eol": (datetime.date.today() - datetime.timedelta(days=1)).isoformat()}
        elif isinstance(eol, str):
            cycles[cycle] = {"eol": eol}
    return cycles


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report the snapshot's age instead of refreshing")
    arguments = parser.parse_args(argv)
    table = json.loads(TABLE.read_text())
    today = datetime.date.today()
    if arguments.check:
        age = today - datetime.date.fromisoformat(table["snapshot"])
        print(f"support table dated {table['snapshot']}: {age.days} day(s) old" + (
            " — stale; run scripts/refresh-support.py" if age > STALE_AFTER else ""
        ))
        return 1 if age > STALE_AFTER else 0
    for key, product in table["products"].items():
        slug = product.get("endoflife")
        if not slug:
            print(f"{key}: kept by hand")
            continue
        fresh = cycles_of(slug)
        if fresh:
            product["cycles"] = dict(sorted(fresh.items(), key=lambda item: [int(p) if p.isdigit() else p
                                                                             for p in item[0].split(".")]))
            print(f"{key}: {len(fresh)} cycle(s) from endoflife.date/{slug}")
        else:
            print(f"{key}: endoflife.date/{slug} returned nothing; kept as it was", file=sys.stderr)
    table["snapshot"] = today.isoformat()
    TABLE.write_text(json.dumps(table, indent=2) + "\n")
    print(f"snapshot dated {table['snapshot']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
