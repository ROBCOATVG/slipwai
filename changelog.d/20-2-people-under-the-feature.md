MINOR

**The people a story signs in as are the feature's to declare.** `specs/<feature>/people/<username>.json` —
`{"username", "name", "password", "realm"}`, with `email` and `roles` where needed — joins the cumulative
artifacts a slice may write; the realm file under `docker/` stays the host's. Try it reads them beside the
realm's users and creates the ones its throwaway sign-in server lacks; `try_it.py people --apply` does the
same for a berth's. A file doubling a realm user, or missing a field, is refused by `check-try` by name.

**Catch-up:** `slipwai migrate` brings `try_it.py` and the ladder's words; run `make agents`. Stories that
name people nobody declared fail `check-try` until the files are written — which is the point.
