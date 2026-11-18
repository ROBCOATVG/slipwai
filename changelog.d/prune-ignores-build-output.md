PATCH

**`slipwai migrate` no longer brings back options a project never chose because of what a build left.**
The pruner counted any file on disk matching an option's patterns as that option installed. A Java service's
`target/` matched the SQLite and external-identity patterns after one `make verify`, so the replay kept their
blocks. lean-coffee-club was then offered a SQLite driver, an Auth0 environment and a customers realm, and
`.env.example` conflicted. A path git ignores is no longer counted.

**Catch-up:** none. The next `slipwai migrate` reads the project correctly.
