MINOR

**The board asks which extensions to elect, and the answer reaches `./init`.** It asked nothing, and the
omission was invisible rather than visible: `./init`'s extension menu reads `/dev/tty` and **prints nothing
where there is none**, so every `./init` the board has ever run elected nothing — silently, because an
empty capture is indistinguishable from a person checking no boxes. A project generated from the board came
out with no extensions and no sign that any had been offered. The only way to get one was to pick a
quickstart that named it, or to run `./init --extension <key>` afterwards in a terminal.

**Dev tooling** now sits beside the `./init` question on the generate form: one checkbox per extension
installed on this machine, each saying what it is for rather than only its key, and the chosen keys are
passed to `./init` as explicit `--extension` flags — which it never second-guesses. The card's first line
is the whole command, so an election is something a person watches happen. Nothing is checked by default,
and the question is not asked at all where the machine has no extensions installed: a question whose every
answer is unavailable is a question not worth asking, and the keel ships none of them.

`interview_page` is split at the seam its own budget note names — the rows and the page script are now
`interview_form`, leaving the questions and the flags they become, which is the pairing that note defends.
