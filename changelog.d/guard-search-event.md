MINOR

**A `before-search` guard is handed the search, and not only the word searched for.** It used to receive
`SLIPWAI_QUERY` and nothing else, so it could not tell a search of `specs/` from a search of the source, a
`Glob` from a `Grep`, a shell command from a pattern, or one session from another. It now reads one JSON
object on its stdin: the tool, the pattern, the path, the glob and file type, the shell command, the
session's directory, and the session and sub-agent that made the call. A field the search did not name is
absent rather than empty. `docs/extensions.md` lists the fields, and a test holds that list to the code.
Every tool-call guard also receives the `SLIPWAI_TOOL` the contract already promised, and `SLIPWAI_POINT`.
A shell command too long to be passed as an argument used to reach no guard at all; it now reaches one.

**Catch-up:** `slipwai migrate` brings the scripts. A guard written against `SLIPWAI_QUERY` needs no
change: that variable carries what it carried, cut at 16,000 characters. An extension author who wants the
rest reads the event from stdin.
