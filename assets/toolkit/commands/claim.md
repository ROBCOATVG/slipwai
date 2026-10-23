---
description: Take a fairway for this machine, give it back, or say who holds each one — the claim a captain takes, taken by hand
argument-hint: [<fairway> | release <fairway>]
---

# Claim

A fairway's claim is `refs/slipwai/claims/<fairway>`, pushed to the forge. A captain takes it before it claims
a slice. A person takes it by hand to divide the fairways between two machines for longer than one `/sail`.

- **No argument:** run `python3 scripts/agents/claims.py`. It prints every fairway the chart has, and who
  holds each one and since when.
- **A fairway:** run `python3 scripts/agents/claims.py --take $ARGUMENTS`, which takes it for this machine.
- **`release <fairway>`:** run `python3 scripts/agents/claims.py --release <fairway>`, which gives it back.

Put every line it printed in your reply, unchanged, in a fenced block, before anything else: the harness folds
a command's output, so what it said reaches a person only through your reply.

**A refusal is the answer.** Where another machine holds the fairway, the script says which machine and since
when. Repeat that, and stop. Do not take it again, and never force the ref: the push a second taker cannot
win is the whole of what makes a claim mean anything.

Where the script notes that this harbour has no `origin`, say that the claim is local to this machine and no
other machine can see it. A claim nobody else can see routes nobody.

A claim is routing, not a lock. The claim on the work itself is still the `slice/<id>` branch, and `/sail`
takes that.
