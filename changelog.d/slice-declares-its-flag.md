PATCH

**A slice declares its own flag, and a story that signs in can get a token.** Before this change, a slice
that introduced a flag could not pass. `check-flags` accepts the declaration only in the same change as the
code that reads it, but `check-slice-scope` refused any slice that touched `infra/service/flags.auto.tfvars`.
The slice handed the line back, and the trunk mender could not land it alone. lean-coffee-club's MT1 parked
for a person over it, and SI1 stubbed sign-in round it. A slice branch may now add a key seeded `off`, with
comments and blank lines. It may still remove or change nothing.

The local `app` realm also had no public client, and the `customers` realm's `web` client refused the
password grant. `try_it.py` uses that grant to sign a story's person in, so every story that signed in stayed
dark with `401 invalid_client`. The `app` realm now ships a public `web` client, and both `web` clients allow
the password grant. These are local fixtures only.

**Catch-up:** `slipwai migrate` carries `scripts/check-slice-scope.py`. The realm under
`docker/keycloak/realms/` is the project's own: add the `web` client by hand, or let a slice hand it back.
