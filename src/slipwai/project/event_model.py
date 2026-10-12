"""Everything about the event model a generated project carries.

Only the event profile gets any of it: the model itself, the two documents that connect it to code, the
workflow that renders it into a browsable page, and the address that page will be served at.

`docs/first-slice.md` is `assets/event-model/first-slice.md` now, and the mapping document is
`model_to_code.py`'s two assets beside it. What is still written here is the block of paths inside that
page's fenced listing, which is rendered from the backend's answer to `EVENT_MODEL_PATHS` and is the
reason the page cannot drift from the files a slice is actually handed (`docs/generated-prose.md`, case
two). The workflow below is not prose and is left for 16.7, which decides what becomes of the templates
that are YAML and shell.
"""
from __future__ import annotations

import os

from ..assets import MODEL_PAGE_ROOT, TOOLKIT_ROOT
from ..backends import NODE_MAJOR, PYTHON_VERSION
from ..registry import EVENT_MODEL_PATHS, registry
from ..services import App
from .metadata import sourced
from .model_to_code import ServiceCode, model_to_code
from .prose import page


def event_model_page_url(project_name: str) -> str:
    """Where the event-model workflow will publish this project's browsable page.

    Both halves belong to whoever is generating rather than to the keel, so both are read from the
    environment. The owner is the Gitea user or organisation the project gets pushed under, from
    `GITEA_OWNER`, never defaulted to a person's name; unset, the link says `your-owner` for the reader to
    replace.

    The host is `GITEA_PAGES_URL` — named for the `GITEA_PAGES_*` family `scripts/gitea-pages.py` reads, and
    for `GITEA_URL` in `scripts/publish-to-gitea.py`, the same kind of value for the forge itself. Its
    default is the local daemon, which is correct for the setup this keel ships and wrong the moment the
    forge is elsewhere: `scripts/gitea-pages.py` serves bare repositories read off a *local* Gitea's disk
    (`GITEA_REPOS_DIR`), so against a remote forge it has nothing to read and this link points at nothing
    while the workflow publishes the `pages` branch perfectly well. Nothing fails; the document just carries
    a dead link. A remote forge must set the variable, and `docs/publishing.md` says so beside the owner.
    """
    owner = os.environ.get("GITEA_OWNER", "your-owner")
    base = os.environ.get("GITEA_PAGES_URL", "http://localhost:3301").rstrip("/")
    return f"{base}/{owner}/{project_name}/"


def code_paths(project_name: str, service: App) -> dict[str, str]:
    """Where one service's code lands, as its backend answers it, with `repository` filled where it has not.

    `repository` joined the four keys with the state-stored rung (15.6): the port a service that keeps
    current state loads and saves through, where an event-sourced one has its event store. A backend
    written before the rung was a question answers four, and this page is about where code goes rather than
    about the protocol — so the port is shown with the decision it belongs to, which is where a language
    that has not split it out keeps it, and `slipwai package check` is what tells that language to answer
    the key. The fill is for one MINOR, and is never reached on the `events` rung: nothing there reads it.
    """
    paths = registry().answer(service.backend, EVENT_MODEL_PATHS)(project_name, service.path)
    return {**paths, "repository": paths.get("repository", paths["domain"])}


FIRST_SLICE = "first-slice.md"
#: What `assets/event-model/first-slice.md` may name, and the whole of what it may name. Pooled with
#: `model_to_code.TOKENS` by `tests/test_generated_prose.py`, which holds the tree in both directions.
TOKENS = ("write-identity", "slice-files")


def first_slice_values(project_name: str, first: App) -> dict[str, str]:
    """The fenced listing in `docs/first-slice.md`: the files one slice opens, where this backend puts them.

    A table of paths rendered from the declaration that decides them, which is why it is a value and not
    an asset — a hand-written listing is a second answer to a question `EVENT_MODEL_PATHS` already
    answers, and the first slice would be told to open a file nobody generated.

    The port is in the tree only on the rung that has one: on `events` the store a slice appends to is
    named in the write-model table, not here, and a line for it would be a file the first slice is told to
    open and will not find.
    """
    paths = code_paths(project_name, first)
    port = "" if sourced(first) else f"\n{paths['repository']}   the port current state is loaded and saved through"
    return {
        "write-identity": "stream identity" if sourced(first) else "the identity a write locks",
        "slice-files": (
            f"{paths['events']}   immutable event definitions\n"
            f"{paths['domain']}   "
            f"{'pure evolve/decide logic' if sourced(first) else 'pure decide logic over current state'}\n"
            f"{paths['usecase']}   orchestration and ports{port}\n"
            f"{paths['test']}   observable behavior"
        ),
    }


def event_documentation(project_name: str, services: list[App]) -> dict[str, str]:
    """The two documents that connect the model to code, with this project's own paths in them.

    `first-slice.md` shows one service's paths, because a page describing the files a slice touches has to
    show a tree somebody can open, and the first service is the one a first slice lands in. The mapping
    document shows every service, because its subject is the write model and that is per service: one table
    would describe the first service's rung and silently hand it to the rest (phase 15.3).
    """
    first, *_ = services
    first_slice = page(MODEL_PAGE_ROOT, FIRST_SLICE, first_slice_values(project_name, first))
    mapping = model_to_code([
        ServiceCode(service.path, sourced(service), code_paths(project_name, service))
        for service in services
    ])
    # The asset is the canonical template, with its guidance comments intact. The one generated change is
    # the page address: unlike a template, a generated project knows where its pages daemon will serve it.
    model = (TOOLKIT_ROOT / "docs/event-model/model.yaml").read_text(encoding="utf-8").replace(
        "  # page: https://your-org.github.io/your-repo/",
        f"  page: {event_model_page_url(project_name)}",
    )
    if f"page: {event_model_page_url(project_name)}" not in model:
        raise ValueError("model.yaml asset lost its page placeholder — update event_documentation")
    return {
        "docs/event-model/model.yaml": model,
        "docs/first-slice.md": first_slice,
        "docs/event-modeling-to-code.md": mapping,
    }


def event_model_workflow(make: str = "make") -> str:
    # `make` is how the render step invokes the Makefile from the root (`Layout.make`). Renders docs/event-model/model.yaml into the browsable page — the styled timeline with per-slice
    # views and embedded mockups — using the vendored TypeScript pipeline. mermaid-cli drives a headless
    # Chromium, so this path-filtered workflow is the only place that browser is paid for; `make verify`
    # keeps its browser-free Python validation. On GitHub the site deploys through the Pages API; on Gitea
    # (told apart by github.server_url) it is force-pushed to the `pages` branch, which the local
    # gitea-pages daemon serves at $GITEA_PAGES_URL/<owner>/<repo>/. The pages branch is build output
    # with no history worth keeping, and the push token is the run's ephemeral one.
    return """name: event model
on:
  push:
    branches: [main]
    paths:
      - 'docs/event-model/**'
      - 'scripts/event-model/**'
      - '.github/workflows/event-model.yml'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  render:
    runs-on: ubuntu-latest
    # Only this job writes, and only to the `pages` branch below. The file-level default stays read-only.
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '__PYTHON_VERSION__'
      # Fail loudly on an invalid model before spending a browser on it.
      - run: python3 scripts/event-model/check.py
      - uses: actions/setup-node@v6
        with:
          node-version: '__NODE_MAJOR__'

      # `make model` drives mermaid-cli, which drives Chromium through Puppeteer, and Chromium's sandbox
      # needs unprivileged user namespaces. Ubuntu 24.04 restricts those with an AppArmor profile, so the
      # browser dies at startup with "No usable sandbox!" before drawing anything. Re-enabling namespaces
      # on the runner is the fix; passing `--no-sandbox` unconditionally would turn the sandbox off in
      # every environment to work around one runner's policy.
      #
      # Three runners to satisfy, not two. A GitHub-hosted Ubuntu 24.04 runner restricts namespaces and
      # lets us relax them. A runner image that never restricted them has no such file. And a **container**
      # runner - which is what Gitea Actions gives you - has the file but mounts /proc/sys read-only, so
      # the write is refused. Testing `-e` treated that third case as the first: `tee` failed with
      # "Read-only file system" and, under `-e -o pipefail`, took the job down before it drew anything.
      #
      # So: try, and treat a refusal as information rather than failure. A container that cannot relax the
      # policy also cannot use the namespace sandbox, and the step below already knows how to fetch a
      # Chromium that does not need one - this tells it to.
      - name: Let Chromium have its sandbox back
        run: |
          sysctl=/proc/sys/kernel/apparmor_restrict_unprivileged_userns
          if [ ! -e "$sysctl" ]; then
            echo "$sysctl: absent, so this runner never restricted user namespaces"
          elif echo 0 | sudo tee "$sysctl" >/dev/null 2>&1; then
            echo "$sysctl: unprivileged user namespaces re-enabled"
          else
            echo "$sysctl: not writable, as on a container runner; using a Chromium that needs no sandbox"
            echo "SANDBOX_UNAVAILABLE=1" >> "$GITHUB_ENV"
          fi

      # mermaid-cli's Puppeteer downloads Chrome for Testing, which Google publishes no linux/arm64 build
      # of, so `make model` dies at the browser fetch on Apple-silicon hardware — the manual workaround
      # docs/event-model/README.md describes, done automatically here.
      #
      # The condition is `uname -m` rather than the `runner.arch` expression context on purpose: this
      # workflow also runs on third-party runners, which need not populate that context, and the question
      # being asked is genuinely about the machine. An x86_64 runner that could relax the AppArmor policy
      # exits at the first line and never pays for the download.
      #
      # The second reason to take this path has nothing to do with architecture: a container runner on any
      # architecture cannot use the namespace sandbox and cannot turn the restriction off, which the step
      # above detects and reports as SANDBOX_UNAVAILABLE. Both cases need the same thing - a Chromium this
      # machine can actually start - so they share one step rather than growing a second copy of it.
      #
      # `MERMAID_PUPPETEER_CONFIG` is the escape hatch scripts/event-model/render.ts already reads, so
      # "Render the model" below needs no change. `--no-sandbox` is required because Chromium's own sandbox
      # cannot initialise inside an already unprivileged container, and `--disable-dev-shm-usage` avoids
      # crashes from the small /dev/shm most containers mount. It is reached only where the sandbox was
      # never going to start, which is the distinction the comment above is drawing.
      - name: A Chromium that can start on this runner
        run: |
          set -eu
          case "$(uname -m)" in
            aarch64|arm64) ;;
            *)
              if [ -z "${SANDBOX_UNAVAILABLE:-}" ]; then
                echo "$(uname -m): Chrome for Testing publishes a build for this architecture, and the sandbox works"
                exit 0
              fi
              echo "$(uname -m): no usable namespace sandbox on this runner"
              ;;
          esac
          npx -y playwright@1.62.1 install --with-deps chromium-headless-shell
          # Both names, because Playwright renamed the executable: the archive is now
          # chrome-headless-shell-linux64.zip and the binary inside it is `chrome-headless-shell`, where an
          # older pinned Playwright still produces `headless_shell`. This workflow runs on runners the
          # project does not own, so it should not assume which of the two it will be handed.
          headless="$(find "$HOME/.cache/ms-playwright" -type f \\( -name headless_shell -o -name chrome-headless-shell \\) | head -1)"
          [ -x "$headless" ] || { echo "no headless shell binary under $HOME/.cache/ms-playwright" >&2; exit 1; }
          "$headless" --version
          config="${RUNNER_TEMP:-/tmp}/mermaid-puppeteer.json"
          cat > "$config" <<JSON
          {"executablePath": "$headless", "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
          JSON
          echo "MERMAID_PUPPETEER_CONFIG=$config" >> "$GITHUB_ENV"

      # An empty model is the correct state until the first modelling session. `make model` says so and
      # writes nothing, which is why the assembly below tolerates finding no page.
      - name: Render the model
        run: make model

      # The page links its SVGs and mockups relative to itself, so the directory is the unit that gets
      # published. index.html is a copy rather than a rename so a link to model.html keeps working.
      - name: Assemble the site
        run: |
          mkdir -p _site
          if [ -f docs/event-model/model.html ]; then
            cp -R docs/event-model/. _site/
            rm -rf _site/node_modules
            cp docs/event-model/model.html _site/index.html
          else
            echo '<!doctype html><title>Event model</title><p>No slices yet — model your first workflow, then run <code>make model</code>.' > _site/index.html
          fi

      # A downloadable copy of the site on the run. upload-artifact v4 speaks an artifact API that only
      # github.com has and refuses to start anywhere else ("not currently supported on GHES"), Gitea
      # included; Gitea implements the v3 protocol, so every other forge gets v3 of the same action.
      - uses: actions/upload-artifact@v4
        if: github.server_url == 'https://github.com'
        with:
          name: event-model
          path: _site
          retention-days: 90
      - uses: actions/upload-artifact@v3
        if: github.server_url != 'https://github.com'
        with:
          name: event-model
          path: _site
          retention-days: 90
      # Off GitHub, publishing is a branch push and nothing more. A Codeberg-Pages-style server — the
      # gitea-pages daemon among them — serves whatever sits at the tip of a repository's `pages` branch,
      # with the branch root as the site root; there is no API to call and no OIDC token to exchange, so
      # `actions/deploy-pages` has no equivalent here and the `deploy` job below is skipped instead.
      #
      # One orphan commit, force-pushed, which is the old gh-pages convention and the right shape for this:
      # the server reads only the tip, so accumulating a commit per run would grow the repository by the
      # size of every SVG ever rendered in exchange for history nobody reads. `_site/` becomes its own
      # throwaway repository so the job's `main` checkout is never touched.
      #
      # A custom domain, if one is ever wanted, is a `.domains` file at the root of this branch — write it
      # into `_site/` here from a repository variable rather than guessing at a hostname.
      #
      # `github.token` is what Gitea Actions exposes for same-repo operations, under the same name as on
      # GitHub; checkout's own credential is read-oriented, so the push carries this one explicitly. The URL
      # is built from `github.server_url`, so this is not tied to one instance.
      - name: Publish to the pages branch (non-GitHub forge)
        if: github.server_url != 'https://github.com' && github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          git -C _site init -b pages
          git -C _site -c user.name=gitea-actions -c user.email=actions@localhost add -A
          git -C _site -c user.name=gitea-actions -c user.email=actions@localhost commit -m "Publish event model from ${GITHUB_SHA}"
          proto="${GITHUB_SERVER_URL%%://*}"
          host="${GITHUB_SERVER_URL#*://}"
          git -C _site push --force "${proto}://${GITHUB_ACTOR}:${GITHUB_TOKEN}@${host}/${GITHUB_REPOSITORY}.git" HEAD:refs/heads/pages
      - name: Package for GitHub Pages
        if: github.server_url == 'https://github.com'
        uses: actions/upload-pages-artifact@v3
        with:
          path: _site

  deploy:
    needs: render
    if: github.server_url == 'https://github.com'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
""".replace("__NODE_MAJOR__", str(NODE_MAJOR)).replace("__PYTHON_VERSION__", PYTHON_VERSION).replace("run: make model", f"run: {make} model")  # the verify workflow's toolchain versions, from the one constant each of them reads, rather than a second literal; tokens because an f-string would have to double every brace in the YAML above
