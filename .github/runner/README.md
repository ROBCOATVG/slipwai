# The CI job image

Every `runs-on: ubuntu-latest` job in this repository runs in an image built from this directory. It carries
every toolchain the factory's suite needs — Python, Node, Go, a JDK, `tofu`, `ko` and `pack` — so no job
installs one.

## Why

The suite generates a project of any catalog backend and runs its native `make verify`, so *every* job needs
*every* toolchain. That used to be seven `actions/setup-*` steps per job. A job container is discarded when
the job ends, so all seven downloaded again in the next one — about a minute of every job, ten jobs a run —
and each setup action asks `api.github.com` which version to fetch. Unauthenticated, that is 60 requests an
hour for the whole runner host, which a single run exhausted; the steps then fell back to downloading
directly, which worked but was slower still and hid the problem.

Baking the toolchains in removes both. `.github/actions/toolchains` no longer installs anything: it runs
[`check-toolchains.sh`](check-toolchains.sh), which reads [`versions.env`](versions.env) **from the
checkout** and holds the running image to it. That direction matters — an image that checked itself would
always agree with itself. Read against the repository, a rebuild that never happened or a runner still
pointing at an old tag fails the first job of the run, naming the tool and both versions.

## The files

| File | What it is |
|---|---|
| `versions.env` | Every toolchain version and archive digest. The only place these numbers are written. |
| `Dockerfile` | The image. Takes every version as a `--build-arg`, with no defaults. |
| `fetch.sh` | Download-and-verify, used for each archive at build time. |
| `build.sh` | Sources `versions.env` and builds. The only supported way to build. |
| `check-toolchains.sh` | Holds a running image to `versions.env`. What CI runs each job. |

## Bump a toolchain

Edit the version and its digest in `versions.env`, rebuild, retag, restart the runners. Nothing else — and
in particular no workflow file — mentions a toolchain version.

```sh
.github/runner/build.sh slipwai-ci:$(date +%F)
```

The build runs from the repository root (that is where `build.sh` points `docker build`, because the image
warms pip's wheel cache from the three committed `requirements-*.txt`). `.dockerignore` keeps the context to
those files and this directory.

Prove it before rolling it out — this is exactly what CI will run:

```sh
docker run --rm -v "$PWD:/repo" -w /repo slipwai-ci:$(date +%F) .github/runner/check-toolchains.sh
```

## Roll it out

The image lives on the runner host and is never pushed to a registry: act_runner starts job containers
through that host's own Docker daemon, so a local tag is all it needs.

Build it on the host from a checkout of the branch, or build it elsewhere and ship it:

```sh
docker save slipwai-ci:2026-09-04 | ssh gitea 'docker load'
```

Then, in the runner config (`/opt/gitea/runner-config-v3.yaml` — one file, shared by all four runners):

```yaml
runner:
  labels:
    - "ubuntu-latest:docker://slipwai-ci:2026-09-04"
container:
  force_pull: false        # the tag is local; pulling would look for it on a registry and fail
```

Wait until no run is in progress — restarting a runner kills the job it is running — then:

```sh
cd /opt/gitea && docker compose restart runner1 runner2 runner3 runner4
```

Two things about that config file, both learned the hard way:

- It is bind-mounted **as a single file**, and Docker resolves a single-file bind to an inode when the
  container is created. Replacing it with `mv` or `scp` gives it a new inode, and `docker compose restart`
  then keeps serving the *old* file. Edit it in place, and check with
  `docker exec gitea-runner1-1 grep slipwai-ci /config.yaml` before restarting.
- Keep `container.options` and `container.valid_volumes` as they are. They carry the `--add-host` that lets
  a job reach the shared actions/cache server from its per-job network.

## What the image does not carry

`package.yml` and `publish-package.yml` still use `actions/setup-python`. They run only on a `v*` tag, so
they were left alone; they would work without it, and dropping it would take their last `api.github.com`
call with it.

Go's `GOTOOLCHAIN` is left at its default. Every generated `go.mod` pins a version at or below the image's
Go, so nothing downloads a toolchain today — but a generated pin above it would, silently and per job.

The pip wheel cache baked into the image goes stale when a `requirements-*.txt` changes. That costs a
download and nothing else: pip fetches what the cache lacks. It is a speed question, never a correctness
one, and a rebuild refreshes it.
