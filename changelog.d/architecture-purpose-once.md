PATCH

**The architecture page states a service's purpose once.** Under *Bounded contexts*, `docs/architecture.md`
used to print a service's whole purpose under every context it holds. A service with seven contexts printed
the same paragraph seven times, and that is what conflicted when such a project was migrated. A context now
names only the service it lives in. The purpose stays on the services line at the top of the page, and
beside the context when a service holds just one.

**Catch-up:** `slipwai migrate` rewrites the page. A project that kept its own version during an earlier
conflict gets the *Bounded contexts* list on its next migration.
