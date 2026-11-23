MINOR

**A hand-back that needs the slice's own code now lands with the slice's merge, and a product question is
no longer sent to the mender.** A slice that needs a change to a file it may not write can now carry it as
a patch in its own record, `specs/<feature>/slices/<id>/handback/<name>.patch`, with its reason in the prose
above the diff. At that slice's merge the harbourmaster applies each patch on the slice rebased onto trunk,
in its merge's scratch tree, and runs the one full gate over both: both land, or the merge is refused and
neither does. A patch that no longer applies refuses the slice with it. A patch that touches a gate or the
cloud under `infra/` (other than the flag declaration) is not applied; the `granted` line names it under
`withheld`, and it stays a need for a person. On manda 43 mender jobs failed because a hand-back sent on its
own needed the slice's unmerged code, failed the full gate without it, or cited what only the slice's branch
held.

A need that is a product or model decision — `fleet.py tell --need … --check decide --slice <id>`, or a
need checked in the chart, the event model or the story split — is now also written as a `question` against
the slice, so the skipper decides it under `/cruise` and the person under `/sail`, and the `decision` that
answers it ticks the need. The mender never takes one. Prose needs work as before for everything that
cannot be a patch.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/harbourmaster.py`, `mender.py`, `fleet.py`
and `commands/sail.md`; a slice in flight that already raised a prose need keeps it, and one written from
now on can hand back a patch instead.
