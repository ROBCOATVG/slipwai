PATCH

**A migration no longer offers to delete the PRD and design material you handed over at generate time.**
The replay wrote only what the recorded answers regenerate, and the scaffold commit held `docs/prd.md`, the
files under `docs/design/` and `.slipwai/quickstart.json` beside the factory's, so git read the factory's side
as having deleted them and a clean merge took the deletion. The replay now carries those files from the base
commit as they were there, and lists them in `docs/README.md` as generate did, so the merge sees the factory
leaving them alone and keeps whatever the project has made of them since.

**Catch-up:** if a migration already took the deletion, `git checkout <commit before it> -- docs/prd.md
docs/design .slipwai/quickstart.json` brings them back; commit them and the next migration leaves them alone.
