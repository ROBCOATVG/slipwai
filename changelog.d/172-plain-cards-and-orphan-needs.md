MINOR

**Waiting on you holds only what waits on you, each card says who acts and why, and it leads with a sentence
in plain English.** manda's board showed seven things *Waiting on you* and one of them needed a person. The
rest were the fleet's own work, stranded, and every card was in the slice agent's words for another agent.

- **A plain line on every need and question.** `fleet.py tell --need` now takes a `--plain` per need: one or
  two sentences saying what is wrong and why it matters, with no paths, ids or line numbers. It is held to the
  rule a decision's **In short** is held to (one rule, `NOT_PLAIN`, now in the logs module and used by
  `check-decisions` too), and a need without one is refused. A question asked for a decision carries its
  need's plain line. The board and `slipwai fleet` lead with it and keep the agent's words under *Details*;
  a card written before there was a plain line still draws, and says the wording is the agent's own.
- **The card says who acts.** A need the mender takes is drawn as *The mender will do this*, in a card of its
  own beside *Waiting on you* and not counted as a wait. *Have the mender try again* appears only where the
  mender would take the need and has spent its attempts. A need that is a person's says why: the cloud, a
  secret, nothing on trunk can prove it, an open slice is changing the file.
- **No orphans.** A need on source or tests is the mender's where no open slice's branch changes that path,
  and so is a merged slice's own folder; the full gate is still what lets it land. A hand-back that names
  its patch lands with its slice's (or careen's) merge instead of being asked as a decision, and a patch to
  the model or the chart lands there only where it adds no name the code does not already have and removes
  or renames none; otherwise it is withheld as a decision. `NEVER` and the cloud rule are as they were.
- **Stale cards close themselves.** A question whose need is met, or whose slice has merged and which a
  recorded decision it cites answers, gets a `question-met` and leaves the board; a decision need of a
  merged slice that cites a recorded decision gets a `need-met` saying so. A text check's `has` was already
  read with one pair of surrounding quotes trimmed; the mender's brief now quotes it the same way.
- **An attempt that changes nothing says why.** The staff-directory need that the mender tried twelve times
  and never committed was pinned by a test, and a test was never a need's to change. The mender may now
  change it with the seed in one commit. Where it still cannot land a need, it writes its reason, the
  `mend-failed` line carries it as `declined`, the card shows it, and it is not sent again until a person
  presses *Have the mender try again*.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/need_owner.py` and the changed mender,
harbourmaster, `fleet.py`, `check-decisions.py` and the mender's brief. A session that raises a need now
passes `--plain`; older lines need nothing.
