"""Which pages a project going to production is given, and the words the README borrows from its target.

A managed target's `docs/deployment.md` and `docs/adr/0002-production-target.md` are entirely that cloud's:
its nodes, its products, its prices, its consequences. There is no general version of either to parameterise
— the attempt would be a page of conditionals describing nothing in particular — so each target brings its
own, as the `docs_pages` member of its `TARGET`.

Until phase 10 this module was a table saying which keel module wrote them, with one module per cloud beside
it. The table is gone: a target package answers `docs_pages` and the keel asks. What is left here is the
asking, the rows the README adds to *Before `./init`* from the same `TARGET`, and the README's *Production*
section itself: that section is the target's and the shape's from its first word to its last, and a skiff
says something a liner's nouns cannot be substituted into — one environment, no promotion — so the section
and the pages it points at are written from one row, in one module, and cannot disagree about what this
project runs on.

The paths are the same for every target on purpose: a reader who has seen one generated project knows where
the drawing and the decision record are, whatever it deploys to, and `slipwai migrate` merges them across a
change of neither name nor number.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..deployment_shapes import row
from ..errors import GenerationError
from ..loaded_targets import answer, cloud_of
from ..services import App
from ..target_protocol import DOCS_PAGES, PREREQUISITES, README_WORDS
from ..targets import managed
from .existing import EXISTING_README


def pages(project_name: str, apps: list[App], target: str, shape: str = "liner") -> dict[str, str]:
    """Both pages for this target, written from this project's own answers."""
    built = answer(target, DOCS_PAGES, default={})
    if not built:
        raise GenerationError(
            f"the {target} target provisions infrastructure but answers no docs_pages: a managed target "
            f"arrives with its drawing and its decision record, which is what `docs_pages` is"
        )
    files = {path: build(project_name, apps) for path, build in built.items()}
    if choice := row(target, shape):
        detail = (f"Compute: {choice['compute']}.\n\nDatabase: {choice['database']}.\n\n"
                  f"{choice['guidance']}\n\n## Changing shape\n\n{choice['transition']}\n")
        files["infra/README.md"] = f"""# {shape.title()} infrastructure

{detail}
## Bootstrap and deploy

Run `make bootstrap` once with the account credentials described in the project's README. Keep its state
passphrase safely: the encrypted bootstrap state and passphrase are needed to read the pipeline's outputs.
The command configures the forge with those outputs. Re-run it after adding a service/image repository.

`make deploy ENV=production` is the production pipeline's apply; run it locally only with the explicitly
provided deploy credentials. `make smoke URL=$(make -s url ENV=production)` proves the resulting endpoint.
Run `tofu init -backend=false -input=false` and `tofu validate` inside each stack to validate it without
applying resources. This check is not a live cloud-connectivity proof.
"""
        if shape == "skiff":
            files["docs/adr/0002-production-target.md"] = f"# Skiff target decision\n\n{detail}"
            files["docs/deployment.md"] = f"""# {project_name}: skiff deployment

Every commit whose main-branch verify gate passes builds and pushes immutable images, deploys the one
production environment and runs its smoke probe. Rollback re-applies the previously recorded images;
there is no staging or promotion workflow. The application's image, gate and flag reader stay the same.

{detail}
"""
    return files


def prerequisites(target: str) -> tuple[tuple[str, str], ...]:
    """The README's *Before `./init`* table, middle rows only: what this cloud in particular asks of the
    machine that runs the first day's work.

    The rows around them — Python, the forge, the repository URL, somewhere to keep the passphrase — are the
    same wherever a project deploys, so they stay in `readme.py` and these are numbered into the middle of
    them. Each row is what to have and what proves it is there.
    """
    return tuple(answer(target, PREREQUISITES, default=()) or ())


def words(target: str) -> dict[str, str]:
    """The nouns the README's *Production* section is written round: what `infra/` runs a service as, what a
    browser app is served from, and what `make bootstrap` looks for.

    Words rather than a second copy of the section, because everything around them — the pipeline,
    `AUTO_PROMOTE`, the rollback workflow, what `make bootstrap` does once — is the same promise whatever
    the cloud is.
    """
    return dict(answer(target, README_WORDS, default={}) or {})


def production_readme(target: str, services: list[App], web: list[App], shape: str = "liner") -> str:
    """The README's account of where this project goes to production, for a project that goes anywhere."""
    if target == "existing":
        return EXISTING_README
    if not managed(CATALOG, target):
        return ""
    if shape == "skiff" and (choice := row(target, shape)):
        return f"""
## Production

This project's skiff deploys one production environment. Every verified main-branch commit builds and
pushes immutable images, deploys production and proves its endpoint with a smoke check. There is no
staging promotion step. Compute is {choice['compute']}; the database is {choice['database']}.

```sh
make bootstrap                    # configure the account and forge once, with explicit credentials
make deploy ENV=production        # the pipeline's deployment operation
make smoke URL=$(make -s url ENV=production)
make rollback ENV=production      # restore the recorded previous images
```

[Deployment details](docs/deployment.md) and [infrastructure operations](infra/README.md) describe this
shape. `slipwai converge --shape liner` prepares a proposed change and its data-preserving cutover runbook;
it never applies infrastructure or discards the current database.
"""
    nouns = words(target)
    site = nouns["site"] if web else ""
    return f"""
## Production

This project deploys to {cloud_of(target)}, and the pipeline is the way it gets there: every commit that passes `verify` on
`main` runs `.github/workflows/deploy.yml`, which builds one image per service with the ecosystem's own
builder, pushes each by digest, applies `staging`, proves it with `make smoke`, applies `production` and
proves that. It starts when `verify` completes, and only if it passed — never beside it or ahead of it.{site}

Whether that last step runs is the `AUTO_PROMOTE` variable `make bootstrap` wrote to the forge. `true`,
the default, is the pipeline just described. `false` stops it at staging: production is deployed by
`.github/workflows/production.yml` instead, started by `make promote` or from the Actions tab, with the
commit staging is running — and without auto-promotion that first promotion is also what creates
production, so a project pays for one environment until it wants two. Either way production is only ever given the images
staging has already run, and the apply happens on the runner with the deploy role, never on a laptop.
`make bootstrap AUTO_PROMOTE=true` changes this project's mind, in either direction.

When a release is wrong, `.github/workflows/rollback.yml` is started by hand from the Actions tab with the
environment to roll back; it re-applies the release before the current one and proves it the same way.
`infra/` is the whole of the infrastructure — OpenTofu, {nouns["runtime"]} — [`docs/deployment.md`](docs/deployment.md) draws it for this project's services, and
[`docs/adr/0002-production-target.md`](docs/adr/0002-production-target.md) is why each part is what it is, with what it costs.

```sh
make build smoke-image PLATFORM=linux/arm64   # every service's image, run locally and asked its probe
make deploy ENV=staging                        # what the pipeline does, from a laptop with credentials
make smoke URL=$(make -s url ENV=staging)     # what proves a deploy
make promote                                   # ask the forge to deploy production with what staging runs
make rollback ENV=staging                      # what the rollback workflow does, from a laptop
```

`make bootstrap` is the one thing a person does, once, with the credentials {nouns['credentials']} can
find — `./init` runs it after asking where to push. It applies `infra/bootstrap` — the state bucket, the pipeline's identity, the image repositories — and
configures the repository on the forge from the outputs (variables; and, on a forge without OIDC such as
Gitea, the two secrets of a key that can only assume the deploy role). Run it again after `add-service`.
[`infra/README.md`](infra/README.md) says what it decides and how. `make ci` builds every image and proves
it answers, which is the half of a deploy that can be proved without an account; `tofu validate` is what the
gate holds the stacks to.
"""
