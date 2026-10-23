PATCH

**A state-stored service gets no `seed-<service>` target.** A given is an event appended to a log, and a
service on the state rung keeps none, so the languages ship no seed script there; the Makefile wrote the target
anyway, and Try it ran it and reported a broken door rather than none.

**Catch-up:** `slipwai migrate`; the target leaves a state-stored service's Makefile.
