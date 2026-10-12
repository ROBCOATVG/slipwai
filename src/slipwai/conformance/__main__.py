"""`python -m slipwai.conformance <language-dir> <package>`: the suite from a shell, as a language author runs it.

One line per check, `ok` or `FAILED` with each finding indented under it, or `not run` with the reason, and a last
line saying whether the package passed. Exit 0 when it did, 1 when it did not, 2 for a usage error, and 3 when the
suite itself could not run — never a traceback for any of them.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from ..assets import VERSION
from ..extension_shape import OBLIGATIONS
from .extension import check as check_extension
from .run import CHECKS, Report, check, require_package_name
from .target import CHECKS as TARGET_CHECKS
from .target import MANIFEST as TARGET_MANIFEST
from .target import check as check_target


def lines(report: Report) -> list[str]:
    """The report as the command line prints it."""
    said = [f"conformance: {report.package} in {report.directory}, against slipwai {VERSION}"]
    for name in CHECKS:
        if name in report.not_run:
            said.append(f"  {name:<11} not run: {report.not_run[name]}")
        elif name in report.findings:
            found = report.findings[name]
            said += [f"  {name:<11} {'FAILED' if found else 'ok'}", *(f"    {finding}" for finding in found)]
    count = report.count()
    verdict = "passed" if report.passed else f"failed, {count} finding{'' if count == 1 else 's'}"
    return [*said, f"conformance: {report.package} {verdict}"]


def extension_report(parser: argparse.ArgumentParser, package: Path) -> int:
    """`--extension <dir>`: the six, in the order `docs/extensions.md` sets them."""
    if not (package / "extension.json").is_file():
        parser.error(f"{package} holds no extension.json, so it is not an extension package")
    try:
        report = check_extension(package)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"conformance: the suite could not run: {error}", file=sys.stderr)
        return 3
    print(f"conformance: extension {report.key} in {package}, against slipwai {VERSION}")
    for name, said in OBLIGATIONS:
        if name in report.not_run:
            print(f"  {name:<11} not run: {report.not_run[name]}")
            continue
        found = report.findings.get(name, [])
        print(f"  {name:<11} {'FAILED' if found else 'ok'}  — {said}")
        for finding in found:
            print(f"    {finding}")
    count = report.count()
    print(f"conformance: {report.key} "
          f"{'passed' if report.passed else f'failed, {count} finding' + ('' if count == 1 else 's')}")
    return 0 if report.passed else 1


def target_report(parser: argparse.ArgumentParser, package: Path) -> int:
    """`--target <dir>`: the four a target package is held to, in the order a publisher meets them."""
    if not (package / TARGET_MANIFEST).is_file():
        parser.error(f"{package} holds no {TARGET_MANIFEST}, so it is not a target package")
    try:
        report = check_target(package)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"conformance: the suite could not run: {error}", file=sys.stderr)
        return 3
    print(f"conformance: target {report.name} in {package}, against slipwai {VERSION}")
    for name in TARGET_CHECKS:
        if name in report.not_run:
            print(f"  {name:<11} not run: {report.not_run[name]}")
            continue
        found = report.findings.get(name, [])
        print(f"  {name:<11} {'FAILED' if found else 'ok'}")
        for finding in found:
            print(f"    {finding}")
    count = report.count()
    print(f"conformance: {report.name} "
          f"{'passed' if report.passed else f'failed, {count} finding' + ('' if count == 1 else 's')}")
    return 0 if report.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m slipwai.conformance",
        description="Check a language package against this slipwai: every protocol member, every example marker, "
        "both profiles, every declared target, its prune rows and its version rule.",
    )
    parser.add_argument("--extension", metavar="<dir>", type=Path,
                        help="an extension package instead: the six obligations, run against a scratch project")
    parser.add_argument("--target", metavar="<dir>", type=Path,
                        help="a target package instead: its declaration, its TARGET, both stacks and its version")
    parser.add_argument("language_dir", metavar="language-dir", type=Path, nargs="?",
                        help="the directory holding the package (and, for a framework, its family)")
    parser.add_argument("package", nargs="?", help="the package's directory name in it, e.g. go or java-quarkus")
    args = parser.parse_args(argv)
    if args.extension is not None and args.target is not None:
        parser.error("one package at a time: --extension or --target, not both")
    if args.extension is not None:
        return extension_report(parser, args.extension)
    if args.target is not None:
        return target_report(parser, args.target)
    if args.language_dir is None or args.package is None:
        parser.error("name a language package (<language-dir> <package>), an extension (--extension <dir>) "
                     "or a target (--target <dir>)")
    if not args.language_dir.is_dir():
        parser.error(f"{args.language_dir} is not a directory")
    try:
        require_package_name(args.package)
    except ValueError as error:
        parser.error(str(error))
    # A path that is not text, or a stream that cannot encode it, is printed escaped and never a traceback.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="backslashreplace")
    try:
        report = check(args.language_dir, args.package)
    except (OSError, RuntimeError) as error:
        print(f"conformance: the suite could not run: {error}", file=sys.stderr)
        return 3
    print("\n".join(lines(report)))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
