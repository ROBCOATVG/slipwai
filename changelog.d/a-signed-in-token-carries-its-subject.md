PATCH

**A browser's sign-in carries a subject.** Keycloak 25 moved `sub` into the `basic` client scope, and the `customers` realm's browser client listed its scopes without it, so every token it issued had no `sub` and a service keyed on it refused every signed-in request. The realm now lists `basic`; Try it adds it to its own sign-in server for a project whose realm predates this, and that project's own realm needs the same one-word fix.
