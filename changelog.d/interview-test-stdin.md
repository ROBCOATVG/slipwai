PATCH

**The fast suite no longer hangs when it is started with a standard input nobody closes.** The interview's
order test patches every question the interview asks and counts which were asked; the design prompt
("Everything else: a folder") was not in its list, so that one question read the real standard input. At
a terminal or under `/dev/null` that is end-of-file and the prompt answers "none"; started with a
socket for its standard input it waited forever, which looked like a suite that took all night. The list is
complete now, and says why it has to be.

**Catch-up:** nothing; a test in the keel's own suite.
