PATCH

**A test that hangs fails its CI job in half an hour, and the test that hung no longer can.** Nothing a
project receives changes. The keel's own gate had no time limit on a job, and one test read a captain's
output after ending it at a limit while the sessions it had started still held the pipes; that read never
returned, and a macOS job sat for two hours with trunk's next run queued behind it.

**Catch-up:** nothing; this is the keel's own gate.
