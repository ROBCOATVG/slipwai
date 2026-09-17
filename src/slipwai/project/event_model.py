"""Everything about the event model a generated project carries.

Only the event profile gets any of it: the model itself, the two documents that connect it to code, the
workflow that renders it into a browsable page, and the address that page will be served at.
"""
from __future__ import annotations

import os

from ..assets import TOOLKIT_ROOT
from ..backends import NODE_MAJOR, PYTHON_VERSION
from ..naming import java_package_segment, python_package_name
from .model_to_code import model_to_code


def event_model_page_url(project_name: str) -> str:
    """Where the event-model workflow will publish this project's browsable page.

    Both halves belong to whoever is generating rather than to the factory, so both are read from the
    environment. The owner is the Gitea user or organisation the project gets pushed under, from
    `GITEA_OWNER`, never defaulted to a person's name; unset, the link says `your-owner` for the reader to
    replace.

    The host is `GITEA_PAGES_URL` — named for the `GITEA_PAGES_*` family `scripts/gitea-pages.py` reads, and
    for `GITEA_URL` in `scripts/publish-to-gitea.py`, the same kind of value for the forge itself. Its
    default is the local daemon, which is correct for the setup this factory ships and wrong the moment the
    forge is elsewhere: `scripts/gitea-pages.py` serves bare repositories read off a *local* Gitea's disk
    (`GITEA_REPOS_DIR`), so against a remote forge it has nothing to read and this link points at nothing
    while the workflow publishes the `pages` branch perfectly well. Nothing fails; the document just carries
    a dead link. A remote forge must set the variable, and `docs/publishing.md` says so beside the owner.
    """
    owner = os.environ.get("GITEA_OWNER", "your-owner")
    base = os.environ.get("GITEA_PAGES_URL", "http://localhost:3301").rstrip("/")
    return f"{base}/{owner}/{project_name}/"


def event_documentation(project_name: str, backend: str, service: str = "apps/service") -> dict[str, str]:
    """The two documents that connect the model to code, with paths into the first service.

    One service's paths, because a document has to show one; `service` is the first service's directory, and
    the text says that a slice belonging to another service lives under that service's directory instead.
    """
    documented_python_package = python_package_name(project_name)
    # Java drops the separators rather than replacing them, the way the ecosystem does with a hyphenated
    # artifact name, and a segment that would start with a digit gets the same prefix treatment.
    documented_java_segment = java_package_segment(project_name)
    documented_java_path = f"{service}/src/main/java/com/example/{documented_java_segment}"
    # Every row below lands inside one of the two layers the project ships on day one, because the
    # layers are what `check-imports` and the ESLint rules guard: an event and a decider are the model,
    # a use case is what orchestrates it through a port. A map that pointed at `<context>/` with no
    # layer in it left every one of those rules matching nothing until somebody invented the layout.
    maven_paths = {
        "events": f"{documented_java_path}/domain/<context>/Events.java",
        "domain": f"{documented_java_path}/domain/<context>/Decider.java",
        "usecase": f"{documented_java_path}/application/<context>/<UseCase>.java",
        "test": (
            f"{service}/src/test/java/com/example/{documented_java_segment}"
            "/domain/<context>/<Slice>Test.java (JUnit 5)"
        ),
    }
    paths = {
        "typescript": {
            "events": f"{service}/src/domain/<context>/events.ts",
            "domain": f"{service}/src/domain/<context>/decider.ts",
            "usecase": f"{service}/src/application/<context>/<use-case>.ts",
            "test": f"{service}/tests/<slice>.test.ts (Vitest)",
        },
        "python": {
            "events": f"{service}/src/{documented_python_package}/domain/<context>/events.py",
            "domain": f"{service}/src/{documented_python_package}/domain/<context>/decider.py",
            "usecase": f"{service}/src/{documented_python_package}/application/<context>/<use_case>.py",
            "test": f"{service}/tests/test_<slice>.py (pytest)",
        },
        "go": {
            "events": f"{service}/domain/<context>/events.go",
            "domain": f"{service}/domain/<context>/decider.go",
            "usecase": f"{service}/application/<context>/usecase.go",
            "test": f"{service}/domain/<context>/<slice>_test.go (testing)",
        },
        # Both Java backends, because these are Maven's source roots rather than a framework's.
        "java-quarkus": maven_paths,
        "java-spring": maven_paths,
    }[backend]
    first_slice = f"""# Writing the first slice

Use `/drive` at any point. It derives the first incomplete stage from artifacts rather than conversation
memory, stepping back above the slice loop when scope has not been specified, modelled, or split yet, and
drives one actor-visible path to its demo.

## Files a slice normally touches

```text
specs/<feature>/slices/<id>/examples.md   rules, examples, Given/When/Then
docs/event-model/model.yaml               timeline, stream identity, event contract
{paths['events']}   immutable event definitions
{paths['domain']}   pure evolve/decide logic
{paths['usecase']}   orchestration and ports
{paths['test']}   observable behavior
```

Add delivery or driven adapters only when the slice crosses those boundaries. A modelled screen is part of
the same vertical slice; do not ship only the backend beneath the white box.

## Artifact lifetime

Feature scope and cumulative contracts stay in the feature directory. A slice's plan, research, data model,
quickstart and tasks live under `specs/<feature>/slices/<id>/` from the day they are written: the canonical
paths the Spec Kit commands resolve to (`specs/<feature>/plan.md` and the other four) are links into that
directory, made by `/drive` before the plan command runs, ignored by git and never committed — so two slices
planned at once never overwrite each other's record. Given/When/Then examples live there from the day they
are mapped. Finishing a slice marks it done rather than moving it: `status: implemented` in the model, which
the ready set and the progress board both read. A `slices/README.md` register — one row per slice, accepted
when it is — is worth its ten lines, so the next slice does not re-derive the convention.

The demo is a feedback boundary, not completion. Route feedback to the stage that owns it, demonstrate the
revision, then—after acceptance—run an adversarial pass where this slice changed attack surface or closed
the split, mutation analysis where configured, and `make verify` before the ready slices (not done, every
`depends_on` done). Every unclaimed ready slice whose contract is settled — `planned` in the model — runs
concurrently, one delegate per slice on a `slice/<id>` branch in its own worktree, merged in split order and
held to the shared-surface rule by `make check-slice-scope` (`commands/drive.md`, *Running ready slices
concurrently*); a harness that cannot delegate takes the earliest in split order and names the rest.
"""
    mapping = model_to_code(backend, service, paths)
    # The asset is the canonical template, with its guidance comments intact. The one generated change is
    # the page address: unlike a template, a generated project knows where its pages daemon will serve it.
    model = (TOOLKIT_ROOT / "docs/event-model/model.yaml").read_text().replace(
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
