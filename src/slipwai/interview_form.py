"""The interview as a page: the rows, the two things a static form cannot do, and the refusal card.

Split from `interview_page` at the seam its budget note names. That module is the interview's one list of
questions, each held in step with the terminal's, and the half that turns the answers back into the flags
`generate` takes — a pairing worth keeping in one file. None of that is true of *rendering* them: a row is
a label and a control, and which control depends on the kind of question rather than on which flag it
becomes.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .errors import GenerationError
from .folder_field import SCRIPT as CHOOSING
from .folder_field import folder_field
from .interview_page import (
    DECLINE,
    WAS,
    Question,
    asked,
    extensions_asked,
    given,
    init_asked,
    repository_asked,
)
from .page_shell import WORKS, document, esc


def field_html(question: Question) -> str:
    """One question, as a row of the form. The `id` is the name: the label has always said `for` and had
    nothing to point at, so clicking one focused nothing and the browser reported fifteen of them."""
    if question.kind == "checks":
        # Checkboxes and not a multiple-select: every row's name and what it is for has to be readable at
        # once, which is the whole reason a person can answer this on a page and not in `./init`'s menu.
        asking = '<div class="checks">' + "".join(
            f'<label class="check"><input type="checkbox" name="{esc(question.name)}" value="{esc(name)}"'
            f'{" checked" if name in question.default.split(",") else ""}>'
            f"<span>{esc(question.labels.get(name, name))}</span></label>" for name in question.choices
        ) + "</div>"
    elif question.choices:
        options = "".join(
            f'<option value="{esc(name)}"{" selected" if name == question.default else ""}>'
            f"{esc(question.labels.get(name, name))}</option>" for name in question.choices)
        asking = f'<select id="{esc(question.name)}" name="{esc(question.name)}" data-asks>{options}</select>'
    elif question.kind == "path":
        asking = folder_field(question.name, question.default)
    elif question.kind == "file":
        asking = (f'<input id="{esc(question.name)}" name="{esc(question.name)}" type="file" '
                  f'accept=".md,.markdown,.txt,text/markdown,text/plain">')
    else:
        asking = (f'<input id="{esc(question.name)}" name="{esc(question.name)}" value="{esc(question.default)}"'
                  f'{"" if question.optional else " required"}>')
    why = f'<div class="why">{esc(question.why)}</div>' if question.why else ""
    no = "".join(f'<div class="no">{esc(name)} — {esc(line)}</div>'
                 for name, line in question.unavailable.items())
    return (f'<div class="q"><label for="{esc(question.name)}">{esc(question.label)}</label>'
            f"{asking}{why}{no}</div>")


def form(answers: Mapping[str, str], root: Path | None = None) -> str:
    """The whole interview, as one card. Re-rendered when an answer changes what comes after it."""
    rows = "".join(field_html(question) for question in asked(answers, root))
    rows += (f'<input type="hidden" name="{WAS}" '
             f'value="{esc(given(answers).get("quickstart") or DECLINE)}">')
    rows += field_html(init_asked(answers, root or Path(".")))
    # Beside `./init` and not among the generator's flags, because this is `./init`'s own question: the
    # board runs it as a child, and a child has no `/dev/tty` for the menu that would otherwise ask.
    if (offered := extensions_asked(answers)) is not None:
        rows += field_html(offered)
    rows += field_html(repository_asked(answers))
    return (f'<div class="card" id="interview"><h2>Start a new project</h2>'
            f'<form class="ask-page">{rows}</form>'
            f'<div class="ask"><button class="go" id="generate">Generate</button></div>'
            f'<pre class="said" id="said" data-tail hidden></pre></div>')


#: The two things the page does that a static form cannot. An answer to a question that decides a later one
#: — the target decides which languages are offered, the backend decides which axes apply — is asked again
#: rather than patched, because deciding in the browser which questions follow would be the second reading
#: of the catalogue this slice exists to avoid.
SCRIPT = WORKS + CHOOSING + """
// A file input's entry is a File, which JSON would render as `{}`: it is read here and sent as its text,
// with its name beside it, and only when it is about to be used — a re-ask of the questions is sent the
// name alone.
const answers = async (withFiles) => {
  const form = document.querySelector('form.ask-page');
  const held = Object.fromEntries(new FormData(form).entries());
  // A checkbox group sends one entry per checked box under one name, and `fromEntries` keeps the last of
  // them: three checked would arrive as one. Joined here, which is how the verb and `./init` take a list.
  for (const group of form.querySelectorAll('.checks')) {
    const name = group.querySelector('input').name;
    held[name] = [...group.querySelectorAll('input:checked')].map(one => one.value).join(',');
  }
  for (const [name, value] of Object.entries(held)) {
    if (!(value instanceof File)) continue;
    held[name] = withFiles && value.size ? await value.text() : '';
    if (value.size) held[name + '-name'] = value.name;
  }
  return held;
};

async function post(path, withFiles){
  return fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                      body: JSON.stringify(await answers(withFiles))});
}
document.addEventListener('change', async event => {
  if (!event.target.matches('[data-asks]')) return;
  // The form is rendered again from the catalogue, and a chosen file does not survive that unless carried.
  const chosen = document.getElementById('prd');
  const files = chosen && chosen.files.length ? chosen.files : null;
  const answer = await post('/generate/ask', false);
  if (!answer.ok) return;
  document.getElementById('interview').outerHTML = await answer.text();
  const again = document.getElementById('prd');
  if (again && files) again.files = files;
});
document.addEventListener('click', async event => {
  if (event.target.id !== 'generate') return;
  const said = document.getElementById('said');
  said.hidden = false;
  said.className = 'said';
  said.textContent = 'generating…';
  // The longest press on this board: a tree written, committed, and `./init` started in it. The button
  // says so itself rather than only the log below, which on a long form is off the bottom of the screen.
  const was = working(event.target, 'Generating…');
  let answer;
  try {
    answer = await post('/generate/run', true);
    said.textContent = await answer.text();
  } catch (fault) {
    said.textContent = 'the board could not be reached: ' + fault;
    said.className = 'said bad';
    return;
  } finally { was(); }
  said.scrollTop = said.scrollHeight;
  if (!answer.ok) { said.className = 'said bad'; return; }
  // Made. This window is the new project's window from here, and the voyage opens beside it rather than
  // over it: a run is watched for an afternoon and this window is where the next project is started from.
  // `look` and not this window's seat, so the two are genuinely two — a Look here typed in this one later
  // moves this one, and the run goes on being watched where it was opened.
  const receipt = await (await fetch('/init.json')).json();
  window.open('/voyage?look=' + encodeURIComponent(receipt.root), '_blank', 'noopener');
});
"""


def nothing(refused: GenerationError) -> str:
    """The card a board with no language to generate on shows: what is missing, and the tab that fixes it.

    The terminal answers this with `nothing_to_generate`, which prints an install line per language the
    chandlery offers — the right answer for somebody who can type one. Here the install is a tab away, so
    the page says that instead; the refusal itself is still shown, because it is the sentence that says why.

    Before this, the questions were asked of a catalogue with no backend in it and the refusal came out of
    the server as a closed connection — which is what a person met on the first machine they ever installed
    this on, where no language is installed yet by definition.
    """
    return ('<div class="card"><h2>There is no language to generate with yet</h2>'
            f'<p class="empty">{esc(refused)}</p>'
            '<dl><dt><a href="/packages">Install a language</a></dt>'
            "<dd>this page asks its questions the moment there is one</dd></dl></div>")


def page(answers: Mapping[str, str], title: str = "Start a new project", root: Path | None = None) -> str:
    """The interview as a page of its own. 14.4 makes it a tab of the board; the questions do not change."""
    try:
        body, sub = form(answers, root), f"{len(asked(answers))} questions, read from the catalogue"
    except GenerationError as refused:
        return document(title, "nothing to generate yet", nothing(refused), now="/generate")
    return document(title, sub, body, SCRIPT, now="/generate")
