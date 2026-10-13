MINOR

**A crossing reads a backing-service block by its marker, not by the file it sits in.** The factory's own
file and a project's replacement for it both carry `# backing-service:<feature>:begin`, so one block
implemented twice is a fact the migration can simply see — and now does. A file the offering adds whose
every block this project already implements somewhere else is not taken, and is listed on the catch-up
page with the file that already holds it.

This is the general form of the fault that made a crossing restore a deleted stack. A factory *rename*
arrives as an addition, not a change: the offered path is one the project has never had, so there is no
deletion to conflict with and nothing to resolve. The rename table saves the ordinary case by moving the
project's own file to the new name first; this saves the case where the project's answer was never the
factory's file under any name.

**A crossing now reads the project's stacks when it has finished**, and says what it found. A generated
project's gate runs with no provider plugins and no cloud credential by design, so until now the first
thing to read those files for real was the deploy. The structural reading needs nothing installed — a name
two files of one stack both declare refuses the whole stack — and `tofu validate` adds to it wherever a
tool is installed and initialised. It never refuses: the merge is already committed, and a crossing that
failed over a stack it is not allowed to touch would be the worse answer.

**Pruning deletes a file it empties.** A marked file whose every region was dropped was written back as
zero bytes and stayed there for ever — invisible in a diff, carried through every replay, renamed along
with everything else.

**A crossing no longer dates flags it cannot date.** It used to stamp `# hoisted: <today>` onto every line
of every `flags.auto.tfvars`, flags that were off included. To hoist a flag is to turn it on for real
actors, so that is a claim about a product that never happened, written into a file a person owns — and
`check-flags` counts its thirty-day strike window from that date without looking at the value, so a
stamped off flag is reported a month later as having been on everywhere. The flags that are on and
undated are named on the catch-up page instead, for the person who knows when each went on.

**Catch-up:** nothing. If an earlier crossing stamped your flags, the dates are still there and still
wrong: delete the ones that were never true.
