"""A folder, asked for on a page: the button that opens this machine's dialog, and the field it fills in.

Two pages ask for a folder — the interview, for where the project is made and where the brief is, and the
adoption tab, for the repository — and a person should meet the same control on both. Before this the
interview had it and the adoption tab was a text box, which is what a person noticed first.
"""
from __future__ import annotations

from pathlib import Path

from .folder_choice import asking
from .page_shell import esc


def folder_field(name: str, value: str, required: bool = False) -> str:
    """A button and the folder it chose, not a file input. A browser may not learn where anything is on the
    disk — that is the rule, not an oversight — so the board asks the machine for it with the same dialog
    every other program on this computer opens. Only where this machine has no such dialog is the path
    typed, and then the field is an ordinary one."""
    field = (f'<input id="{esc(name)}" name="{esc(name)}" value="{esc(value)}" '
             f'placeholder="a folder on this machine"{" required" if required else ""}')
    if not asking(Path.home()):
        return f'<div class="path">{field}></div>'
    return (f'<div class="path">{field} readonly data-choose="{esc(name)}">'
            f'<button type="button" class="install" data-choose="{esc(name)}">Choose folder…</button></div>')


#: The page half. The board is on this machine, so it opens the dialog and hands back where it landed; a
#: cancel comes back empty and the field keeps what it had. Not a reload: this fills a field in and the rest
#: of the form stays put. The field itself is a way in too, and both are held while the dialog is open.
SCRIPT = """
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-choose]');
  if (!button) return;
  const box = document.getElementById(button.dataset.choose);
  const doors = document.querySelectorAll(`[data-choose="${button.dataset.choose}"]`);
  doors.forEach(door => { door.disabled = true; });
  try {
    const answer = await fetch('/choose', {method:'POST', headers:{'Content-Type':'application/json'},
                                           body: JSON.stringify({start: box.value, field: box.id})});
    const picked = (await answer.text()).trim();
    if (picked) { box.value = picked; box.dispatchEvent(new Event('change', {bubbles: true})); }
  } finally { doors.forEach(door => { door.disabled = false; }); }
});
"""
