MINOR

**A slice's window has its example map.** The examples a slice is built and demoed against were a file on
its branch that nobody on the board was shown. A slice's window now has two tabs, *Where it is* (what it
showed before) and *Example map*, drawn from the slice's own `examples.md`: the story across the top, a
column a rule with its examples under it, and the questions last. An example is a button that opens in place
on its Given, When and Then, and says *Proven by a test* once `tasks.md`'s `## Examples proven` names it
beside a test. A question is red while open and faded once its line says what answered it. A line under the
story counts it all: `11 rules · 16 examples · 4 questions, 1 open · 14 of 16 proven`.
- **Read from where the slice is.** Its `slice/<id>` branch while it is in flight, trunk's working tree once
  that branch is merged, and read again only when the branch or the files move.
- **The tab is in the address**, so a reload keeps it, and the window's poll swaps the map only when the
  file changed, with the examples a person opened opened again and the row of rules where they scrolled it.
- **A done slice has a window too**, linked from its card at its map. A card in flight says the counts under
  its Examples step: `11 rules · 16 examples · 1 question open`.
- **A file that strays from the shape is a partial map**, never an error: a rule with no example yet still
  shows, a scenario written as a list keeps its words, and a slice with no file says it has no map yet.

**Catch-up:** nothing to run: the window and the card are the board's, and read the files a slice already
writes.
