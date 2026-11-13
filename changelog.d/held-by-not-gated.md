PATCH

**A fleet taking or releasing a fairway no longer fails `make verify` on trunk.** The split's `held_by`
column is filled in from the claim refs. `make check-rendered` used to check it against those refs, which
change whenever a captain takes or gives back a fairway. So trunk went red mid-run, and the only fix was to
commit a machine's name. The check now leaves `held_by` alone. `make decisions` still writes it from the
refs, and a name typed in by hand is still overwritten at the next fold.

**Catch-up:** `slipwai migrate` carries the new `scripts/render-fairways.py` and the Makefile's help line.
