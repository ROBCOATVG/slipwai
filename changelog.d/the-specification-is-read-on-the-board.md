PATCH

**Open spec shows the specification, not its markup.** The button beside Continue the build served
`specs/<feature>/spec.md` as `text/plain` — a wall of hashes and asterisks in a browser window, which is
the format for a machine. Being asked to say a document is good and handed its source is being asked to
agree to something nobody has shown you.

It is rendered now, in the board's own shell, titled by the document's own first heading. The renderer is
the keel's own and about a hundred lines: no markdown library ships with this, and what has to be rendered
is not the whole of CommonMark but what `/draft` and `/mockups` write — headings, both kinds of list and
their nesting, tables, rules, fenced code, and bold, italic, code and links inside a line. Everything the
document says is text: a tag in the source is shown, never run.
