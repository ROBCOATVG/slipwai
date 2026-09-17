"""The questions `generate` asks when run bare, one per answer, each refusing until it has a legal one.

Split from `cli.py`, which keeps the flags and the assembly: a question is the interactive spelling of a
flag, and the two grew apart in size long before they grew apart in meaning. Every prompt raises
`GenerationError` at end-of-input, so a script that forgot a flag is told which one rather than hanging.
"""
from __future__ import annotations

import re
import shutil
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path

# Raw-mode reading is POSIX only; where it is missing every list question is asked typed.
try:
    import termios
    import tty
except ImportError:  # pragma: no cover - Windows
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

from .catalog import (
    CATALOG,
    axis_default,
    axis_options,
    axis_required,
    families,
    framework_of,
    resolve_backend,
)
from .errors import GenerationError
from .services import check_context, check_name
from .targets import offered_backends


def validate_project_name(name: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name) or name in {".", ".."}:
        raise GenerationError(
            "project name must start with a lowercase letter or number and contain only lowercase "
            "letters, numbers, '.', '_' or '-'"
        )


def prompt_project_name() -> str:
    while True:
        try:
            name = input("Project name: ").strip()
        except EOFError as error:
            raise GenerationError("project name is required; pass it as an argument in non-interactive use") from error
        try:
            validate_project_name(name)
        except GenerationError as error:
            print(f"Invalid project name: {error}", file=sys.stderr)
            continue
        return name


def prompt_choice(
    label: str, choices: list[str], default: str, describe: Callable[[str], str] | None = None,
    question: str | None = None,
) -> str:
    """Ask one question with a fixed list of answers.

    In a terminal this is a list to move through with the arrow keys — the way Spec Kit asks which agent —
    so an answer is never mistyped and every row shows what it means. Anywhere else (a pipe, a script, a
    terminal this cannot put in raw mode) it is the typed question it always was, with the rows printed
    first where there is anything to say about them: that path is what tests and non-interactive callers
    drive, and it has to keep working unchanged.

    `question`, where given, is the full sentence printed above the rows while they are live, so the reader
    knows what the list is an answer to before choosing; `label` is the short name the chosen answer is
    written against afterwards. A caller that has already printed its question passes only the label.
    """
    if terminal_can_select():
        return select_in_terminal(label, choices, default, describe, question)
    if question is not None:
        print(question)
    if describe is not None:
        for name in choices:
            print(f"  {name} — {describe(name)}")
    rendered = "/".join(choices)
    while True:
        try:
            answer = input(f"{label} ({rendered}) [{default}]: ").strip()
        except EOFError as error:
            raise GenerationError(f"{label.lower()} is required in non-interactive use") from error
        value = answer or default
        if value in choices:
            return value
        print(f"Invalid {label.lower()}: choose one of {rendered}", file=sys.stderr)


def terminal_can_select() -> bool:
    """Whether both ends are a terminal this process can put in raw mode: not a pipe, not a redirect, and
    a platform with termios (which Windows lacks — it gets the typed question)."""
    return termios is not None and sys.stdin.isatty() and sys.stdout.isatty()


def read_key() -> str:
    """One keypress, with an arrow key's escape sequence read whole."""
    key = sys.stdin.read(1)
    if key == "\x1b":
        # ESC [ A/B — the cursor keys. Read the two bytes that follow; anything else was a bare Escape.
        key += sys.stdin.read(2)
    return key


def select_in_terminal(
    label: str, choices: list[str], default: str, describe: Callable[[str], str] | None,
    question: str | None = None,
) -> str:
    """The arrow-key menu: ↑/↓ (or k/j) move, Enter chooses, a letter jumps to the first answer starting with
    it, Escape or Ctrl-C leaves. Redrawn in place on every key, wrapped to the terminal's width so a long
    description does not throw the redraw off. The question, where there is one, stands above the rows the
    whole time and goes with them when the list collapses to its answer."""
    assert termios is not None and tty is not None
    index = choices.index(default)
    width = max(shutil.get_terminal_size().columns, 40)
    heading = textwrap.wrap(question, width - 1) if question else []

    def rows(selected: int) -> list[str]:
        lines: list[str] = []
        for i, name in enumerate(choices):
            text = f"{name} — {describe(name)}" if describe is not None else name
            wrapped = textwrap.wrap(text, width - 4) or [text]
            marker = "❯" if i == selected else " "
            lines.append(f"  {marker} {wrapped[0]}")
            lines += [f"    {line}" for line in wrapped[1:]]
        return lines

    drawn = rows(index)
    out = sys.stdout
    out.write("\x1b[?25l")  # hide the cursor while the list is live
    out.write("".join(f"{line}\n" for line in heading))
    out.write("\n".join(drawn) + "\n")
    out.flush()
    settings = termios.tcgetattr(sys.stdin.fileno())
    try:
        # TCSANOW rather than setcbreak's default TCSAFLUSH: a key pressed while the list was being drawn is
        # an answer, not noise to discard — and a driver feeding keys through a pty sends it exactly then.
        tty.setcbreak(sys.stdin.fileno(), termios.TCSANOW)
        while True:
            key = read_key()
            if key in ("\r", "\n"):
                break
            if key in ("\x03", "\x1b"):
                raise KeyboardInterrupt
            if key in ("\x1b[A", "k"):
                index = (index - 1) % len(choices)
            elif key in ("\x1b[B", "j"):
                index = (index + 1) % len(choices)
            elif key.isalnum():
                match = next((i for i, name in enumerate(choices) if name.startswith(key.lower())), None)
                if match is None:
                    continue
                index = match
            else:
                continue
            # Back up over what was drawn, clear it, draw again.
            out.write(f"\x1b[{len(drawn)}A\x1b[J")
            drawn = rows(index)
            out.write("\n".join(drawn) + "\n")
            out.flush()
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, settings)
        out.write("\x1b[?25h")
    # Collapse the list — and the question above it — to the answer, in the shape the typed question leaves.
    out.write(f"\x1b[{len(drawn) + len(heading)}A\x1b[J{label}: {choices[index]}\n")
    out.flush()
    return choices[index]


def prompt_yes_no(question: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"{question} [{suffix}]: ").strip().lower()
        except EOFError as error:
            raise GenerationError(f"{question.lower()} is required in non-interactive use") from error
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Invalid answer: enter yes or no", file=sys.stderr)


# Why the recommendation is asymmetric, in the place where the choice is actually made. This is the one
# question a generated project can never answer again — every axis can be answered down later, the profile
# cannot — and the two directions do not cost the same, which inverts the usual "don't buy architecture you
# cannot name a requirement for" instinct. Kept short enough to read at a prompt; the argument in full is in
# `docs/axes.md`.
PROFILE_GUIDANCE = (
    "Only one direction is cheap. An event log folds down into tables whenever you decide it should, so a\n"
    "project can stop being event-sourced; state cannot be turned back into history it never recorded, so\n"
    '"start standard and adopt events where a subdomain earns it" is an option that mostly does not exist.\n'
    "What Event Modeling promises is flat cost per slice, not a cheap start: event upcasting and PII\n"
    "erasure are fixed costs to pay before growth arrives, not slice-shaped ones. Persisted projections\n"
    "were a third until the skeleton started shipping them."
)


def prompt_profile() -> str:
    """Ask which delivery foundation, showing what each one costs and which way the decision can be walked.

    Both answers are written out first, for the reason the axes are: `standard` and `event-modelling` look
    like more-or-less of the same thing until somebody reads that only one of them is the choice you can
    change your mind about. The question itself stays a yes/no rather than becoming a two-option menu,
    because this factory does make a recommendation here — a menu would present them as equals.
    """
    print("\nDelivery foundation:")
    recommended = CATALOG["default"]["profile"]
    ordered = [recommended] + [name for name in CATALOG["profiles"] if name != recommended]
    for name in ordered:
        print(f"  {name} — {CATALOG['profiles'][name]['label']}")
    print(f"\n{PROFILE_GUIDANCE}")
    return (
        "event-modelling"
        if prompt_yes_no("Use Event Modeling?", recommended == "event-modelling")
        else "standard"
    )


def prompt_axis(axis: str, profile: str, backend: str, target: str) -> str:
    """Ask one axis, showing what each answer means.

    The label matters more than the option name here: "postgres" and "sqlite" look interchangeable until
    somebody reads that only one of them can prove a concurrency guarantee.
    """
    spec = CATALOG["axes"][axis]
    options = axis_options(axis, backend, target)
    default = axis_default(axis, backend, target)
    # A target that deploys this axis's answer takes the no-infrastructure one off the menu rather than
    # offering it and refusing it a moment later.
    if axis_required(axis, target):
        options = [name for name in options if name != spec["absent"]]
    print(f"\n{spec['prompt']}:")
    print(f"  {spec['description']}\n")
    return prompt_choice("Choose", options, default, lambda name: spec["options"][name]["label"])


def prompt_target() -> str:
    """Ask where the project goes to production — only when the catalog offers more than one place.

    Asked right after the foundation because the answer decides the menus that follow. With `none` the only
    target there is no question to ask, by the rule every other prompt here follows: one answer is not a
    choice.
    """
    if len(CATALOG["targets"]) == 1:
        return CATALOG["default"]["target"]
    print("\nProduction target:")
    return prompt_choice(
        "Choose", list(CATALOG["targets"]), CATALOG["default"]["target"],
        lambda name: CATALOG["targets"][name]["label"],
    )


def prompt_framework(language: str, target: str) -> str:
    """Ask which framework owns this language's startup, and return the backend that names.

    Not asked at all where the family has one member — the same rule the axes follow: something with one
    answer is not a choice, and offering it teaches the reader that it is. So Go and Python are one
    question, and a language with two frameworks behind it is two. Only the members offered under the
    chosen target are on the menu, which is the same filter the axes apply.
    """
    members = [name for name in families()[language] if name in offered_backends(CATALOG, target)]
    if len(members) == 1:
        return members[0]
    print("\nApplication framework:")
    labels = {
        framework: CATALOG["backends"][name]["label"]
        for name in members
        if (framework := framework_of(name)) is not None
    }
    chosen = prompt_choice(
        "Choose",
        list(labels),
        CATALOG["default"]["framework"][language],
        lambda framework: labels[framework],
    )
    return resolve_backend(language, chosen)


def prompt_application_name(label: str, default: str, taken: set[str]) -> str:
    """Ask what an application is called, refusing a name that cannot be a directory, a package and a
    Compose service at once, or that another application already has."""
    while True:
        try:
            answer = input(f"{label} [{default}]: ").strip() or default
        except EOFError as error:
            raise GenerationError(f"{label.lower()} is required in non-interactive use") from error
        try:
            check_name([], answer)
            if answer in taken:
                raise GenerationError(f"'{answer}' is already the name of another application")
        except GenerationError as error:
            print(f"Invalid {label.lower()}: {error}", file=sys.stderr)
            continue
        return answer


def prompt_purpose(service: str) -> str | None:
    """Ask what the first service owns. Blank is allowed — a first service owns everything until there is a
    second — but the question is asked, because the answer is what the delivery loop places work against."""
    try:
        answer = input(f"What does {service} own? (a sentence or two; Enter to decide later): ").strip()
    except EOFError as error:
        raise GenerationError("the service's purpose is required in non-interactive use") from error
    return answer or None


def prompt_context(service: str) -> list[str] | None:
    """Ask which bounded contexts the first service holds — itself unless told otherwise, and several when
    the product starts as one service with more than one context inside it."""
    while True:
        try:
            answer = input(f"Bounded contexts {service} holds, comma-separated [{service}]: ").strip()
        except EOFError as error:
            raise GenerationError("the service's bounded contexts are required in non-interactive use") from error
        names = [name.strip() for name in answer.split(",") if name.strip()]
        if not names or names == [service]:
            return None
        try:
            for name in names:
                check_context(name)
        except GenerationError as error:
            print(f"Invalid bounded context: {error}", file=sys.stderr)
            continue
        return names


def prompt_output(default: Path) -> Path:
    try:
        answer = input(f"Output parent [{default}]: ").strip()
    except EOFError as error:
        raise GenerationError("output parent is required in non-interactive use") from error
    return Path(answer).expanduser() if answer else default
