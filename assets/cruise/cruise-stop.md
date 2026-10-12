---
description: Ask the harbourmaster and every captain to stop; each stops at its next boundary with its work committed
---

# Cruise stop

A person's stop. Every captain is asked, and each stops **at its next boundary** — it finishes the stage in
hand, writes its lines, commits what is green, and ends. Nothing is killed mid-stage, because a stage ended
halfway leaves a berth whose state nobody can read; a boundary is the point at which stopping costs nothing.

```sh
python3 {{fleet}} stop
```

{{verbatim}} It names each process it asked and says which were already gone — a captain that exited on its own
is a fact worth seeing, and a `stop` that pretended to tidy it is how a person stops believing the output.
Then say that stopping is not undoing: every slice already merged stays merged, every berth stays where it is,
and `{{make}} cruise` casts off again from exactly here. Where nothing was running, the script says so
and nothing is written.
