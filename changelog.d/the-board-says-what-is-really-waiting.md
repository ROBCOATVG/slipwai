PATCH

**The board stops saying a running fleet is waiting on you.** A `told` left *Waiting on you* only when a `read`
receipt named it, and nothing wrote one — so every `go` and `decide for me` a person ever sent stayed there, the
Slices step went red, and it said "make cruise-tell answers a park" while the fleet ran and nothing was parked. A
`told` is now answered by a later `decision`, or — sent while the fairway was parked — by the captain claiming
work again; a note a session leaves for the host while the fairway works still waits for a person. The step also
read a fleet at work as `todo`: it looked for a berth `running`, a state the board never gives. And with the
fleet running, the step says so instead of telling you to cast off.

**A slice run abreast no longer fails `check-slice-scope` on files the run wrote.** `.slipwai/preflight.json`
and `.slipwai/logs.unread-*/` are ignored in every generated project.

**A skill's script no longer stops `make agents`.** The projection read every file under `skills/` as text,
and the `__pycache__/` a skill's own Python leaves behind is not; it is skipped.

**Catch-up:** add `.slipwai/preflight.json` and `.slipwai/logs.unread-*/` to `.gitignore`; `slipwai replay`
and a merge bring the rest.
