"""`slipwai package new|check|release|register`: the publisher's side of the chandlery, in one verb.

A language, an extension and a target are all packages, found in one directory, read by one loader, built
into one shape of release file, and listed in one index. They differ in what they declare and what the keel
does with it, which is exactly the part a publisher cannot be expected to know by heart — so the verb is one
verb that works out the kind from the manifest, rather than three that would drift apart.

The five read in the order a publisher uses them. `new` writes a package that already loads. `check` runs
the conformance suite for whichever kind it is. `version` cuts a release — the entry assembled from
`changelog.d/`, the number written, the fragments gone — which is what the conformance suite demands and
what nothing could do before. `release` builds the file and the index entry. `register` puts both into a
channel and rebuilds its index — which for a private channel is the whole of publishing, and for
the public one is the commit a pull request carries (6.6).
"""
from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path

from . import ed25519
from .assets import this_command
from .catalog import CORE
from .errors import GenerationError, refuse
from .index_schema import EXTENSION, TARGET
from .package_new import KINDS, VERBS, write
from .package_release import kind_of, register, release
from .package_version import cut


def new_package(parsed: argparse.Namespace) -> None:
    written = write(parsed.kind, parsed.name, Path(parsed.into).expanduser(), CORE["schemaVersion"])
    place = Path(parsed.into) / parsed.name
    print(f"{parsed.kind} {parsed.name}:")
    for path in written:
        print(f"  {path}")
    print("Every TODO in it is a decision the keel cannot make for you. Next:")
    print(f"  {this_command()} package check {place}")


def check_package(root: Path) -> int:
    """Run whichever conformance suite this package's kind has, and return its exit status.

    Resolved first: a language's suite is given the directory holding the package and the package's own
    name — its family lives beside it, and a framework is proved against the family it requires — and `.`
    has neither a parent nor a name until it is made absolute.
    """
    from .conformance.__main__ import main as conformance
    whole = root.resolve()
    kind = kind_of(whole)
    if kind == EXTENSION:
        return conformance(["--extension", str(whole)])
    if kind == TARGET:
        return conformance(["--target", str(whole)])
    return conformance([str(whole.parent), whole.name])


def cut_release(parsed: argparse.Namespace) -> None:
    """Assemble the entry, write VERSION, delete the fragments. The thing a person does before tagging."""
    root = Path(parsed.name).expanduser()
    version, claimed, used = cut(root, parsed.release or None)
    print(f"{root.name} {version}" + (f" — {claimed}" if claimed else ""))
    print(f"  {used} fragment(s) assembled into {root / 'CHANGELOG.md'}, and deleted")
    print("  VERSION written")
    print(f"Read the entry, then: git commit -am 'Release {version}' && git tag -a v{version} "
          f"-m '{root.name} {version}' && git push --follow-tags")


def write_key(parsed: argparse.Namespace) -> None:
    """Make a publisher's Ed25519 key pair: the secret to a file, the public one to the screen.

    The secret never goes to the screen, because a key printed into a terminal is a key in a scrollback
    buffer and in whatever logged the session. The public one does, because the next thing a publisher
    does with it is paste it into the message that tells people what to trust.
    """
    into = Path(parsed.out).expanduser() / f"{parsed.name}.key"
    if into.exists():
        raise GenerationError(f"{into} is already there, and overwriting a signing key would make every "
                              f"release signed with the old one unverifiable. Move it aside first")
    secret = secrets.token_bytes(ed25519.KEY_BYTES)
    into.parent.mkdir(parents=True, exist_ok=True)
    into.write_text(base64.b64encode(secret).decode("ascii") + "\n", encoding="utf-8")
    into.chmod(0o600)
    public = base64.b64encode(ed25519.public_key(secret)).decode("ascii")
    print(f"{parsed.name}'s signing key:")
    print(f"  secret        {into} (0600, never commit it; put it in the secret store CI reads)")
    print(f"  public        {public}")
    print(f"  sign with     {this_command()} package release <directory> --key {into}")
    print(f"  they trust it {this_command()} trust add {parsed.name} --key {public}")


def release_package(parsed: argparse.Namespace) -> None:
    root = Path(parsed.name).expanduser()
    archive, entry_file, entry = release(root, Path(parsed.out).expanduser(), parsed.publisher,
                                        parsed.file_url, key_path(parsed))
    print(f"{entry['kind']} {root.name} {entry['version']}")
    print(f"  file          {archive}")
    print(f"  sha256        {entry['sha256']}")
    print(f"  entry         {entry_file}")
    print(f"  signature     {entry.get('signature', '') and 'ed25519' or 'none (--key signs it)'}")
    print(f"  register it   {this_command()} package register {root} --channel <a channel checkout>")


def key_path(parsed: argparse.Namespace) -> Path | None:
    """The signing key named on the command line, or None. Never guessed at: an unsigned release is an
    honest state, and a keel that went looking for a key would sign with whichever one it found."""
    return Path(parsed.key).expanduser() if parsed.key else None


def register_package(parsed: argparse.Namespace) -> None:
    root = Path(parsed.name).expanduser()
    channel = Path(parsed.channel).expanduser()
    archive, entry_file, index = register(root, channel, parsed.publisher, parsed.file_url,
                                          key_path(parsed))
    print(f"registered in {channel}:")
    print(f"  file          {archive.relative_to(channel) if archive else parsed.file_url}")
    print(f"  entry         {entry_file.relative_to(channel)}")
    print(f"  index         {index.relative_to(channel)}")
    print(f"Serve {channel} and name it in SLIPWAI_CHANDLERY to install from it; "
          f"{this_command()} search lists what it holds")


def package_main(argv: list[str]) -> None:
    prog = f"{this_command()} package"
    parser = argparse.ArgumentParser(
        prog=prog, description="Write, check, build and publish a language, extension or target package")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("name", help="the package's key for `new`; its directory for the others")
    parser.add_argument("--kind", choices=KINDS, default="extension",
                        help="`new` only: what the package is (default: extension). The others read the manifest")
    parser.add_argument("--into", default=".", metavar="<directory>",
                        help="`new` only: where the package directory is written (default: here)")
    parser.add_argument("--out", default="dist", metavar="<directory>",
                        help="`release` only: where the file and its entry are written (default: dist)")
    parser.add_argument("--channel", metavar="<directory>",
                        help="`register` only: a checkout of the channel to publish into")
    parser.add_argument("--release", default="", metavar="<version>",
                        help="`version` only: the number, where it is a decision rather than a sum over "
                             "what the fragments claim")
    parser.add_argument("--publisher", default="", metavar="<identity>",
                        help="who published it, as the index records it and `slipwai show` prints it")
    parser.add_argument("--key", default="", metavar="<file>",
                        help="`release` and `register`: the Ed25519 secret key to sign with, as `package "
                             "key` writes it. A private channel's releases are signed this way; the public "
                             "channel's are signed keyless from CI")
    parser.add_argument("--file-url", default="", metavar="<url>",
                        help="where the release file is, where that is not beside the index — the asset on "
                             "the tag that built it, usually. The channel then holds the entry alone")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "new":
            new_package(parsed)
        elif parsed.verb == "key":
            write_key(parsed)
        elif parsed.verb == "check":
            raise SystemExit(check_package(Path(parsed.name).expanduser()))
        elif parsed.verb == "version":
            cut_release(parsed)
        elif parsed.verb == "release":
            release_package(parsed)
        else:
            if not parsed.channel:
                raise GenerationError(f"`{prog} register <directory> --channel <a channel checkout>` needs "
                                      f"the channel to publish into. A private one is any directory served "
                                      f"as static files; name it in SLIPWAI_CHANDLERY to install from it")
            register_package(parsed)
    except GenerationError as error:
        refuse(prog, error)
