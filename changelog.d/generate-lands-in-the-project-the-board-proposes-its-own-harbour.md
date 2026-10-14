PATCH

**The board proposes the directory it is looking at as the output parent, not the directory its process
happens to hold.** A board started at login holds `/`, so **Start a new project** proposed `/`, and
pressing Generate on any target ended in a traceback from a read-only filesystem. The proposal is now the
board's own root — the harbour it serves, or wherever it was last attached — and the login service is also
started in that directory on all three platforms. `slipwai generate` itself now refuses an output parent it
cannot write in, naming the directory and the flag, instead of tracing back.

**Catch-up:** `slipwai bridge install` again, once, so the service file carries its working directory.
Until then, type the output parent on the form.
