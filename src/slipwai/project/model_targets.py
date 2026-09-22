"""The Makefile targets the event profile adds: the model's gate, and its two renderings.

Two renderings, because they have different properties and a project needs both. `make model` draws the
Mermaid diagrams, the README's segments and the browsable page, and drives a headless browser to do it —
so nothing browser-free can prove its output current, none of it is committed, and `make verify` does not
include it. `make model-drawio` writes one draw.io canvas, which is arithmetic and a string: no browser, no
account, no network. So it *is* committed, and `check-drawio` regenerates it in memory and compares on
every commit, inside `verify`. `check-model` — the model's own validation and its links to the code — is a
different question from whether a drawing is current, and stays exactly as it is.
"""
from __future__ import annotations

# What every target that runs the TypeScript pipeline needs first. Repeated per recipe rather than shared
# through a prerequisite, so each target is one thing to read; with the tree already installed it costs
# about a second and asks the registry nothing.
INSTALL = "npm --prefix scripts/event-model install --no-audit --no-fund --loglevel=error"
TSX = "scripts/event-model/node_modules/.bin/tsx"

MODEL_TARGETS = f"""
.PHONY: check-model
check-model: ## Validate the global event model and its links to implemented code
\tpython3 scripts/event-model/check.py

.PHONY: model
model: ## Regenerate the event-model diagrams and browsable page from model.yaml (needs Node; PNG=1 for a raster copy; MERMAID_PUPPETEER_CONFIG=<json> where Chromium cannot sandbox)
\t{INSTALL}
\t{TSX} scripts/event-model/render.ts

.PHONY: model-drawio
model-drawio: ## Write the committed draw.io canvas, docs/event-model/model.drawio, from model.yaml (needs Node, no browser)
\t{INSTALL}
\t{TSX} scripts/event-model/render-drawio.ts

.PHONY: check-drawio
check-drawio: ## Fail when docs/event-model/model.drawio is missing or no longer matches model.yaml
\t{INSTALL}
\t{TSX} scripts/event-model/render-drawio.ts --check

.PHONY: model-drawio-test
model-drawio-test: ## Run the canvas planner's and serialiser's own tests — no browser, no network
\t{INSTALL}
\t{TSX} --test scripts/event-model/board-plan.test.ts scripts/event-model/drawio.test.ts
"""

# What the event profile adds to `verify`, after `test`: the model's validation, then the canvas's currency.
MODEL_GATES = " check-model check-drawio"


def model_targets(event: bool) -> str:
    """The block, or nothing: a project without the event profile has no model to draw."""
    return MODEL_TARGETS if event else ""
