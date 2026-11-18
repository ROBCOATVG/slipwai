PATCH

**Two messages sent in the same second no longer take each other's place.** A message's id was the second it
was sent and three random bytes, and the file it is written to is named by that id. Two messages that drew
the same three bytes in one second were one file: the second replaced the first where it was still waiting,
and was dropped as a replay where the first had already been handled. Nothing said so. It was rare for a
person typing and not for a script: a thread of 450 messages sent in one second lost one about once in 170
runs, which is how it was found, as a test that failed now and then. An id now carries eight random bytes,
and is drawn again where a waiting or handled message of that conversation already has it.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/talk.py`. Messages already sent keep the ids
they have.
