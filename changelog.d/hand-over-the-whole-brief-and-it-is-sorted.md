MINOR

**Hand over the whole folder your brief is in, and it is sorted for you — on the board as well as in a
terminal.** Carrying what a PRD stands on arrived as two flags and no way to use either from the generate
form, which is where most people start a project.

**Everything else** on the form is a folder picker, and `--brief <dir>` is the same thing typed. Whichever
file in it reads as the requirements document becomes `docs/prd.md`; everything else lands under
`docs/design/`. The document is found three ways, in order of how much each proves: the name a PRD usually
has, a name that says what it is, and the document's own first heading — which survives a file somebody
called `v2-final.md`. A folder with no requirements document in it is an answer rather than a failure: it
is all design material, and the specification is written in the agent the way it always could be. What was
decided is printed, so a wrong guess is visible rather than silent. `--prd` and `--design` still name
either half exactly, and win where both are given.

**A document's links are resolved against the document and contained by the brief**, which are two
different directories and were one. A PRD sitting in `docs/` inside a brief folder may point at
`../wireframes/` and have it carried, and still reach nothing outside the folder handed over.

**`--design` on its own is no longer refused.** `commands/mockups.md` reads `docs/design/` whether or not
a PRD exists, so a brand sheet handed over with the specification written in the agent afterwards is a
direction the mock-up stage follows just the same — the refusal was the keel insisting on a dependency its
own stage does not have.

A brief picked in a browser arrives as names and bytes, because a page is handed a file's contents and
never its path. Every guard the command-line half applies is applied again to it and for a stronger
reason: one reads a directory a person typed, the other reads JSON. A name with `..` in it, an absolute
one, or one naming `.git` is refused rather than written, and the board's request limit is raised to hold
a brief at all — base64 is a third larger than the bytes it carries.
