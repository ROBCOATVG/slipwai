MINOR

**Under `--experimental-intro`, `slipwai adopt` no longer wraps anything: every buildable directory the survey
finds is recorded as a candidate, and which of them is an application is answered by the coding agent, with
the code in front of it.** [ADR 0003](docs/adr/0003-a-wrapped-application-begins-as-a-candidate.md) has the reasoning and
the evidence. `Wrap it as the application …? [Y/n]` defaults to yes and is asked of somebody who has not read
the directory; on the first real monorepo this met, that wrapped three asset bundles and a test suite as
applications, under names taken from their directories, with every `purpose` left blank — and there was no way
back, because a re-survey reports an unwrapped directory but has never removed a record.

So `project.json` gained the state it was missing. `deployables` says what somebody has established;
`candidates` says what was merely found, with the path, the language, the commands the build answers and the
file that found it. It is the same distinction `unrecorded` already draws for every row of the convergence
map, and it is why no un-wrap command had to be written: nothing is wrapped, so nothing needs unwrapping.

What follows from it: **`make verify` refuses while nothing is confirmed** and names what confirms one, because
a gate with nothing to hold has not been given its subject and a green run over zero applications is the false
assurance this exists to prevent. **The terminal asks one question** — the forge — and shows the rest as facts;
the language, the kind, the commands, what each directory owns, where the schema and the infrastructure live,
how a change reaches production and why the work is happening all move to the agent or to a conversation.
**`/ground` opens with the candidates**, one at a time, saying what it thinks each is and why from what it
read, before asking. **`slipwai adopt --confirm <name>`** records the answer — with `--as` for a name that is
not the directory's, and `--kind`, `--purpose`, `--command` and `--hexagonal` for the rest — builds the entry
and regenerates everything that reads it, so `deployables` is never edited by hand; **`--decline <name>`** drops
a candidate with nothing recorded in its place. **`--next`** names confirming as the step before the map's rows.
`--yes` stays the unattended path it has always been: it confirms every candidate as found, and the report now
says plainly that nobody looked.

Default off. Without `--experimental-intro` (or `SLIPWAI_EXPERIMENTAL_INTRO=1`) `adopt` asks exactly what it
asked before, wraps what it always wrapped, and writes no `candidates` key.

**Catch-up.** Nothing. A repository adopted before this has its applications in `deployables` already, which is
confirmation by an earlier factory and is left alone; it has no `candidates` key, which reads as an adoption
with nothing outstanding, and `--confirm` says so rather than inventing work. Two readers of an adopted record
— `--next` and `--refresh` — now tolerate a manifest with no deployables, which is the honest state between
`adopt` and the first confirmation; `add-service` still refuses one, since it needs an application to take a
language and a port from.
