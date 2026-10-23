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

`plugin` is the seventh and takes no package at all: it renders the *keel's* own material — the commands,
the agent types and the skills — into a directory a harness installs, so somebody with no slipwai project
can have `/sail`. It is here rather than in a verb of its own because it is the publisher's job done by the
keel, and the release it is then handed to is the same `register`.
"""
from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path

from . import ed25519, native, plugin
from .assets import VERSION, this_command
from .catalog import CORE
from .errors import GenerationError, refuse
from .harness import keys as harness_keys
from .harness import name_of
from .index_schema import EXTENSION, QUICKSTART, TARGET
from .package_new import KINDS, VERBS, write
from .package_release import kind_of, register, release
from .package_version import cut


def new_package(parsed: argparse.Namespace) -> None:
    parts = tuple(part.strip() for part in parsed.parts.split(",") if part.strip())
    written = write(parsed.kind, parsed.name, Path(parsed.into).expanduser(), CORE["schemaVersion"], parts)
    place = Path(parsed.into) / parsed.name
    print(f"{parsed.kind} {parsed.name}:")
    for path in written:
        print(f"  {path}")
    print("Every TODO in it is a decision the keel cannot make for you. Next:")
    print(f"  {this_command()} package check {place}")


#: Where the decision about which install route is supported is written down (slice 12.4). Printed by both
#: of the conveniences, because a decision on a page nobody opens is a decision nobody has.
ROUTES = "docs/reference/install-routes.md"


def render_plugin(parsed: argparse.Namespace) -> None:
    """Render the keel's own material as a plugin a harness installs with no project generated."""
    into = Path(parsed.name).expanduser()
    written = plugin.write(into, parsed.profile)
    skills = sorted({path.split("/")[1] for path in written if path.startswith("skills/")})
    print(f"plugin {plugin.NAME} {VERSION} ({parsed.profile}): {len(written)} file(s) in {into}")
    # Every file but the skills, which are a catalogue rather than a list somebody reads off a terminal.
    for path in written:
        if not path.startswith("skills/"):
            print(f"  {path}")
    print(f"  skills/ — {len(skills)} skill(s): {', '.join(skills)}")
    print(f"A convenience, not the supported route — {ROUTES} says which is, and what this cannot carry.")
    print(f"Install it from {into}, or publish it:")
    print(f"  {this_command()} package register {into} --channel <a channel checkout>")


def render_harness(parsed: argparse.Namespace) -> None:
    """Lay the same material where one harness that is not Claude Code reads it, from its registry row."""
    if not parsed.harness:
        raise GenerationError(f"`{this_command()} package harness <directory> --harness <key>` needs the "
                              f"harness to render for. There are {len(harness_keys())}: "
                              f"{', '.join(harness_keys())}")
    into = Path(parsed.name).expanduser()
    written = native.write(parsed.harness, into, parsed.profile)
    print(f"{name_of(parsed.harness)} ({parsed.profile}): {len(written)} file(s) in {into}")
    for place in sorted({path.split("/")[0] if "/" in path else path for path in written}):
        held = [path for path in written if path == place or path.startswith(f"{place}/")]
        print(f"  {place:<20} {len(held)} file(s)")
    for line in native.unplaceable(parsed.harness):
        print(f"  not here: {line}")
    print(f"A convenience, not the supported route — {ROUTES} says which is, and what this cannot carry.")
    print(f"Copy these into the project, or into {name_of(parsed.harness)}'s own location for them.")


def check_package(root: Path) -> int:
    """Run whichever conformance suite this package's kind has, and return its exit status.

    Resolved first: a language's suite is given the directory holding the package and the package's own
    name — its family lives beside it, and a framework is proved against the family it requires — and `.`
    has neither a parent nor a name until it is made absolute.
    """
    from .conformance.__main__ import main as conformance
    whole = root.resolve()
    kind = kind_of(whole)
    # A quickstart holds no code, so there is no suite to run it against: what `check` answers for one is
    # whether the document reads, that every package it names is named by a range, and what it would do.
    if kind == QUICKSTART:
        from .cli_quickstart import check_quickstart
        return check_quickstart(whole)
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
        prog=prog,
        description="Write, check, build and publish a language, extension or target package, or render "
                    "the keel's own material as a plugin a harness installs")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("name", help="the package's key for `new`; its directory for the others")
    parser.add_argument("--kind", choices=KINDS, default="extension",
                        help="`new` only: what the package is (default: extension) — a language, an "
                             "extension, a target or a quickstart. The others read the manifest")
    parser.add_argument("--parts", default="backend", metavar="backend|frontend|backend,frontend",
                        help="`new --kind language` only: whether it ships services, browser apps, or both "
                             "(default: backend). See docs/frontend-protocol.md in the keel")
    parser.add_argument("--into", default=".", metavar="<directory>",
                        help="`new` only: where the package directory is written (default: here)")
    parser.add_argument("--out", default="dist", metavar="<directory>",
                        help="`release` only: where the file and its entry are written (default: dist)")
    parser.add_argument("--channel", metavar="<directory>",
                        help="`register` only: a checkout of the channel to publish into")
    parser.add_argument("--profile", default=plugin.DEFAULT_PROFILE, metavar="<profile>",
                        help=f"`plugin` and `harness`: whose material to render "
                             f"(default: {plugin.DEFAULT_PROFILE})")
    parser.add_argument("--harness", default="", metavar="<key>",
                        help="`harness` only: which coding agent to lay the material out for, as "
                             "`registry.json` keys it")
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
        elif parsed.verb == "plugin":
            render_plugin(parsed)
        elif parsed.verb == "harness":
            render_harness(parsed)
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
