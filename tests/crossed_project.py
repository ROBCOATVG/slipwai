"""A project that crossed from version 1, as a fixture: a built browser app and no storyboard anywhere.

The hard case of a further feature. The app has committed screen previews, one page per state, under
`apps/web/screens/`; its own tokens and base stylesheet; routes; an event model whose `ui` frames are
implemented; a `docs/design.md` — and no `specs/<feature>/mockups/` at all, because version 1 had no mock-up
stage. `002-export` is the further feature handed to it.
"""
from __future__ import annotations

import json
from pathlib import Path

FIRST, FURTHER = "001-deals", "002-export"
PREVIEWS = {"deal-console-deals.html": "Deal console — deals", "deal-console-empty.html": "Deal console — empty",
            "new-workspace-empty.html": "New workspace — empty", "sign-in.html": "Sign in"}
MODEL = """\
version: 1
slices:
  - id: S1
    name: Create a workspace
    status: "implemented"
    frames:
      - type: ui
        name: NewWorkspaceForm
        mockups:
          - { state: empty, at: docs/event-model/mockups/new-workspace-empty.html }
      - { type: cmd, name: CreateWorkspace }
  - id: S2
    name: Export the pack
    status: "planned"
    frames:
      - { type: ui, name: ExportPanel }
"""
APP = """\
export function App() {
  return (<Routes>
    <Route path="/" element={<DealConsole />} />
    <Route path="/workspaces/new" element={<NewWorkspace />} />
  </Routes>);
}
"""


def write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def crossed(root: Path) -> Path:
    """The project on disk under `root`, with both features specified and nothing drawn."""
    write(root, "project.json", json.dumps({"deployables": {
        "api": {"kind": "service", "path": "apps/api"},
        "web": {"kind": "web", "path": "apps/web", "port": 5173}}}))
    for name, title in PREVIEWS.items():
        write(root, f"apps/web/screens/{name}", f"<!DOCTYPE html><title>{title}</title><main>{title}</main>")
    write(root, "apps/web/src/styles/tokens.css", ":root{--ink:#111}")
    write(root, "apps/web/src/styles/base.css", "body{color:var(--ink)}")
    write(root, "apps/web/src/App.tsx", APP)
    write(root, "apps/web/package.json", "{}")
    write(root, "docs/design.md", "# Design\n\nThe shell is a navy bar over a white sheet.\n")
    write(root, "docs/event-model/model.yaml", MODEL)
    write(root, f"specs/{FIRST}/spec.md", "# Deals\n")
    write(root, f"specs/{FURTHER}/spec.md", "# Export the pack\n")
    return root


def storyboard(root: Path, feature: str = FURTHER) -> Path:
    """The further feature drawn into what exists: two built screens framed from the app's own previews, the
    deal console as this feature changes it, and the one surface that is new."""
    home = root / "specs" / feature / "mockups"
    write(root, f"specs/{feature}/mockups/deal-console.html",
          '<title>Deal console</title><link rel="stylesheet" href="../../../apps/web/src/styles/tokens.css">'
          '<article class="state"><h2>Export offered</h2></article>')
    write(root, f"specs/{feature}/mockups/export-pack.html",
          '<title>Export pack</title><article class="state"><h2>Ready</h2></article>'
          '<article class="state"><h2>Failed</h2></article>')
    write(root, f"specs/{feature}/mockups/storyboard.html",
          "<title>Storyboard</title>"
          '<iframe data-surface="built" src="../../../apps/web/screens/sign-in.html"></iframe>'
          '<iframe src="../../../apps/web/screens/deal-console-deals.html" data-surface="built"></iframe>'
          '<iframe data-surface="changed" src="deal-console.html"></iframe>'
          '<a data-surface="new" href="export-pack.html">Export pack</a>')
    return home
