PATCH

**`make openapi` writes the service's document where it means to.** The recipe passed a path from the
repository root to `npm --workspace apps/service`, which runs the script inside `apps/service`, so the
document was written nowhere the client build reads — in every berth of hr-test-2. It now passes
`$(CURDIR)/apps/service/openapi.json`.
