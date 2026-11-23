"""A block's action line on a card: `Why:`, the answer it holds, `Do:` and its steps, and Approve and Reject.

The words are `block_actions`'; this draws them, the same on a group under *Waiting on you*, a row of the
inbox and a slice's own card, so the three never say different things about one park. Approve and Reject are
drawn only for a block that waits on a mock-up verdict and only while a drawing waits on one (`park_verdict`);
otherwise the card says where they will appear.
"""
from __future__ import annotations

from typing import Any

from .page_shell import esc

STYLE = """
.act{margin:10px 0 0;padding:10px 12px;border-radius:8px;border:1px solid var(--rule);background:var(--paper);
  font-size:.86rem;display:grid;gap:6px}
.act p{margin:0}.act .lbl{font-weight:600;color:var(--ink)}
.act .held{padding:6px 8px;border-radius:6px;border:1px solid var(--critical);background:var(--critical-soft);
  color:var(--ink);overflow-wrap:anywhere}
.act ol{margin:0;padding-left:20px;display:grid;gap:4px;color:var(--ink-2)}
.act ol li{overflow-wrap:anywhere}
.act .verdict{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.act .verdict input{flex:1;min-width:180px;font:inherit;padding:6px 8px;border-radius:6px;border:1px solid var(--rule)}
"""

#: Approve writes at once; Reject asks for its one line first, in the box beside it.
SCRIPT = """
document.addEventListener('click', async event => {
  const pressed = event.target.closest('[data-park-verdict]');
  if (!pressed) return;
  const data = pressed.dataset, box = document.getElementById(data.box);
  const reason = box ? box.value.trim() : '';
  if (data.parkVerdict === 'reject' && !reason) {
    if (box) { box.focus(); box.placeholder = 'Say in one line what to change, then press Reject'; }
    return;
  }
  pressed.disabled = true;
  const answer = await fetch('/park/verdict', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({fairway: data.fairway, slice: data.slice, of: data.of, feature: data.feature,
                          verdict: data.parkVerdict, reason})});
  if (answer.ok) location.reload(); else { pressed.disabled = false; alert(await answer.text()); }
});
"""


def verdict_html(action: dict[str, Any], fairway: str, slice_id: str, of: str) -> str:
    """Approve, a line for why not, and Reject — where a drawing waits — or where they will appear."""
    feature = str(action.get("verdict") or "")
    if not action.get("ready") or not of:
        return (f'<p class="empty">Approve and Reject appear here once a drawing under specs/{esc(feature or "…")}'
                f'/mockups waits on your verdict.</p>')
    box = f"verdict-{slice_id or fairway}-{of.removeprefix('park:')}"
    # The record is the feature's, as the storyboard's verdict is: say which drawings a press is a verdict on.
    pages = ", ".join(str(page) for page in action.get("pages") or [])
    about = (f'<p class="empty">As on the storyboard, the verdict is written for every drawn surface of '
             f'{esc(feature)}; these wait on one: {esc(pages)}.</p>' if pages else "")
    keys = (f'data-fairway="{esc(fairway)}" data-slice="{esc(slice_id)}" data-of="{esc(of)}" '
            f'data-feature="{esc(feature)}" data-box="{esc(box)}"')
    return (f'{about}<div class="verdict"><button type="button" class="go" data-park-verdict="approve" {keys}>'
            f'Approve</button><input id="{esc(box)}" placeholder="If you reject it: one line on what to change" '
            f'aria-label="Why you reject it"><button type="button" data-park-verdict="reject" {keys}>Reject</button>'
            f"</div>")


def action_html(action: dict[str, Any] | None, controls: bool, fairway: str = "", slice_id: str = "",
                of: str = "") -> str:
    """The action line, drawn: nothing where the row has none."""
    if not action:
        return ""
    held = f'<p class="held">{esc(action["held"])}</p>' if action.get("held") else ""
    steps = "".join(f"<li>{esc(step)}</li>" for step in action.get("do") or [])
    verdict = verdict_html(action, fairway, slice_id, of) if controls and "verdict" in action else ""
    return (f'<div class="act"><p><span class="lbl">Why:</span> {esc(action.get("why", ""))}</p>{held}'
            f'<p class="lbl">Do:</p><ol>{steps}</ol>{verdict}</div>')
