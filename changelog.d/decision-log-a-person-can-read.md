MINOR

**The decision log a person can read.** A decision entry was written by agents for agents — a question citing
requirement and decision numbers, options a paragraph each, a decision reading `(a).` — and a product owner
could not tell from it what had been decided.
- **One plain sentence.** The entry gains `**In short:**`: one sentence a product owner reads without the
  specification open, saying what the product now does, with no requirement, decision or event ids and no file
  names. Whoever decides writes it at the time; `/cruise` and the skipper's brief say so, and the shape the owner
  brief shows has it. `make check-decisions` asks it of every entry written since the rule, and refuses one that
  leans on a requirement, decision or example id as the records write them, a backticked name or a path.
- **Only new entries are held.** `slipwai migrate` writes `.specify/decisions-in-short.json` once, into a project
  that already has decisions (on trunk or in any berth), with the instant it brought the rule in and the slices
  already in flight then. The gate holds only entries whose `When` is at or after it from other slices, so the
  entries a project already has pass as they did; a `When` it cannot read is reported as that. A project made
  under the rule never gets the file, and every entry it writes is held.
- **A card per decision.** The board leads each decision with its sentence — with its question, for an entry
  written before the rule — then the options with the chosen one marked and the recommended one named, who
  decided, how sure, what would change it, and its status; the entry as written is behind "Why, in full".
- **The Decisions tab opens on what nobody has read**, least sure first, then the rest, each grouped by
  capability and then slice, with filters for stream, slice, who decided and status kept in the address. The
  count on the tab is the unread, which is what the decision ceiling counts; "awaiting your confirmation" is a
  status and a filter. The tab is a band of the page's one poll: a decision landing appears without a reload,
  and a card a person has open stays open.
- **Confirm** keeps a record beside the logs (`decisions-confirmed.json`) and writes the read receipt; it edits
  and commits nothing in the project. **Change this** opens the Feedback box with the decision quoted and its
  slice as the context — from a slice's window, the Voyage window's box, with the context in the address.
- **Each slice's window** has a Decisions tab beside "Where it is" and "Example map".
- A person's own answer written straight into the record (`Decided by: human`) is shown as theirs; only a
  deck line's answer was before.

**Catch-up:** run `slipwai migrate` and commit what it writes; it records `.specify/decisions-in-short.json`
once, so your existing decisions keep passing `make check-decisions` and every decision written after it says
what was decided in one sentence. A slice already in flight on its branch picks up the new command pages when
it next takes trunk.
