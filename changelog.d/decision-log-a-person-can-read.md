MINOR

**The decision log a person can read.** A decision entry was written by agents for agents — a question citing
requirement and decision numbers, options a paragraph each, a decision reading `(a).` — and a product owner
could not tell from it what had been decided.
- **One plain sentence.** The entry gains `**In short:**`: one sentence a product owner reads without the
  specification open, saying what the product now does, with no requirement, decision or event ids and no file
  names. Whoever decides writes it at the time; `/cruise` and the skipper's brief say so, and the shape the owner
  brief shows has it. `make check-decisions` asks it of every entry written since the rule, and refuses one that
  leans on an id, a backticked name or a file.
- **Only new entries are held.** `slipwai migrate` writes `.specify/decisions-in-short.json` once, into a project
  that already has decisions, with the instant it brought the rule in. The gate holds only entries whose `When`
  is at or after it, so the entries a project already has pass as they did. A project made under the rule never
  gets the file, and every entry it writes is held.
- **A card per decision.** The board leads each decision with its sentence — with its question, for an entry
  written before the rule — then the options with the chosen one marked and the recommended one named, who
  decided, how sure, what would change it, and its status; the entry as written is behind "Why, in full".
- **The Decisions tab opens on what awaits you.** Decisions `awaiting human confirmation` first, then the rest,
  each grouped by capability and then slice, with filters for stream, slice and who decided kept in the
  address. The count on the tab is what awaits confirmation, and the tab is a band of the page's one poll: a
  decision landing appears without a reload, and a card a person has open stays open.
- **Confirm** sets the entry's `Status` to `confirmed by human <date>` in the checkout that holds it, commits
  that edit where the file had no other change, and writes the read receipt. **Change this** opens the
  Feedback box with the decision quoted and its slice as the context.
- **Each slice's window** has a Decisions tab beside "Where it is" and "Example map".
- A person's own answer written straight into the record (`Decided by: human`) is shown as theirs; only a
  deck line's answer was before.

**Catch-up:** run `slipwai migrate` and commit what it writes; it records `.specify/decisions-in-short.json`
once, so your existing decisions keep passing `make check-decisions` and every decision written after it says
what was decided in one sentence. A slice already in flight on its branch picks up the new command pages when
it next takes trunk.
