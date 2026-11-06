PATCH

**Try it never says `ready` over a process it did not start.** A stop signalled only the process groups it had
recorded, and a service or web server that left its group, or was started by a run whose record was lost,
outlived every stop: each later start could not bind, the old process answered the health check, and Try it
reported `ready` over old code. A stop and a start now free Try it's ports of anything still running in its
workspace, and a start refuses, by pid, a port that something else holds.

**Try it reads a story's answer as JSON only where the service says so, and turns on the flags the settings
declare.** A story that fetched a recap's speech failed with a codec error on the WAV it asked for; it is an
answer with nothing to keep now. A flag declared uncommented in `.env.example` is lit in Try it as a flag the
browser asks for is, so a capability with no screen is tried like the rest.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/try_it.py` to an existing project.
