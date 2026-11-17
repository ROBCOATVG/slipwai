MINOR

**A new project pushed to GitHub starts with a green trunk, even before its cloud is ready.** Two of its own
workflows turned it red from the first push, and while any run on trunk is red the harbourmaster lands
nothing. The `event model` workflow named `actions/upload-artifact@v3` for forges other than GitHub, and
GitHub fails a job for naming that version at all, before any step's `if:` is read; it now names only v4,
on GitHub, and off GitHub the copy of the page is the `pages` branch it already pushed. And `deploy` failed at
the cloud sign-in on every push until `make bootstrap` had written the repository's variables; now, on a
target that says which variable proves the bootstrap ran (Azure's `AZURE_CLIENT_ID`, AWS's
`AWS_DEPLOY_ROLE_ARN`), the deploy, `production.yml` and `rollback.yml` are skipped whole until it is set,
with the reason in the job's name, and deploy as before from the first push after it. A target package
answers this with the new optional `configured` key in its `pipeline`; one that does not gets exactly the
workflows it had.

**The pre-push hook reads slice ids written `MTG-01`.** `check-dispatch` read only ids like `SB7`, so in a
project whose model numbers its slices `MTG-01` it found no plan, said there was no chart and no event model
when there were both, and held nothing. It now reads the hyphenated form where a project's plans use it, and
where plan files exist but name no slice yet it says which files it read.

**Catch-up:** run `slipwai migrate` in a project and commit what it rewrites: it brings the corrected
`event-model.yml`, `deploy.yml`, `production.yml` and `rollback.yml` and the new `scripts/check-dispatch.py`
into the project. Once `check-dispatch` reads your ids it may refuse a push naming a slice no dispatch ledger
accounts for; `make dispatch` before starting a slice is what it asks for.
