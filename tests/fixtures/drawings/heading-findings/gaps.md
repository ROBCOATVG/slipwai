# Gaps in the drafted surfaces — find-gaps, design-mock mode

Feature `001-tracker`. Surveyed over the eleven drafts `01`–`11`, `research.md` and `spec.md`, in a session
nobody was in (`SLIPWAI_STAGE=surfaces`). **Nothing below is decided.**

**Checked:** UI states (loading, empty, partial, error, success, disabled, read-only, offline, stale),
content variance, interaction states, permissions and role, data lifecycle.

**Counts:** 3 Blockers, 6 Should-address, 3 Nice-to-have. Most gaps sit on `04` (outstanding items).

**Answered** (recorded in `../decisions.md`): **G5** by D4 — `conflict-resolved` stands.

---

## Blockers

### G1 — "Interview held" has no scheduled-but-not-yet-held state (`04`, `07`)
FR-010 tracks *held*; creating the calendar event proves the interview is **scheduled**, not held.
- **Question:** When the event is created, does "Interview held" stay outstanding until it happened?
- **Proposed state** `scheduled-not-held` — *Trigger:* event created, its time not yet passed.

### G2 — Consent refused has no state, and it would block the final day forever (`04`)
- **Question:** If the person refuses in writing, is the item complete, or something else?
- **Proposed state** `consent-refused` — *Trigger:* the refusal is recorded.

### G3 — The access list defaults to not found, so the final day can never be confirmed (`04`, `05`)
- **Question:** Is "blocked until an access list is entered" the intended outcome?

## Should-address

### G4 — Equipment with nothing held has no state (`04`)
- **Question:** Does "none held" complete the item?

### G5 — ~~Conflicting final days~~ — answered (D4)
- settled

## Nice-to-have

### G10 — The tokens could be named for what they mean
