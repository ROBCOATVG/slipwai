PATCH

**Go's CI cache is keyed on the files a workspace has.** `actions/setup-go` keys its cache on a root `go.sum`,
and a generated Go project is a workspace — `go.work` and `go.work.sum` at the root, each module's `go.sum`
beside its `go.mod` — so the step found nothing to key on, cached nothing, and said so only as a warning while
the run stayed green and downloaded and compiled every module from cold. `verify.yml` and `deploy.yml` now
name every module's `go.sum` and `go.work.sum` as `cache-dependency-path`.
