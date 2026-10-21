PATCH

**Signing in brings a person back to the page they were on.** Keycloak returns the browser to the app's root, so opening a link to a record, being asked to sign in and doing so landed on the home page with the record gone. Every sign-in now carries the page it started from in OAuth's own `state`, set once in the manager `UsersProvider` gives the provider, so a screen that calls `auth.signinRedirect()` itself gets it too; the callback returns only to a path on the app's own origin, never to an address `state` names elsewhere.
