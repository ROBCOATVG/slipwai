---
name: run-the-app
description: Start, reach and drive {{project-name}} — the foreground path (`make dev`), the container path (`make demo`), the addresses each one serves on, what has to be seeded first, and how far to go before opening a browser. Use when asked to run, start, demo, or screenshot the app, when a slice reaches its demo checkpoint, or when a change has to be seen working rather than only proved by tests.
---

# Running {{project-name}}

| Command | Starts | Use it for |
|---|---|---|
{{path-table}}

`make demo` runs the very same `make dev` inside a container over this checkout, so the two paths cannot
disagree about how this project starts. Nothing is built into an image: an edit is live, and there is no
Dockerfile to fall behind the code.

```sh
{{foreground}}
```

## Before a demo, not during one

{{seed}}

<!-- section: serves -->
## What it serves right now

Until a slice adds a route, {{each-service}} answers its probes and nothing else:

```sh
{{probes}}curl -s {{service-url}}/anything   # {"error":"notFound"}, with the path deliberately not echoed back
```

Do not go looking for more. A slice adds its route in {{where}}{{screen}}, and the
404 shape above is the contract everything unmatched keeps.
<!-- end section -->
<!-- section: proxy-check -->

The dev server forwards `/api/*` to the service with the prefix intact, so a slice's route is the same path
on both sides. That also makes one command prove the wiring end to end before any route exists:

```sh
curl -s {{web-url}}/api{{health-path}}     # {"error":"notFound"} — from the *service*, so the proxy is working
```

HTML back instead means the request never left the dev server. `{{health-path}}` is deliberately outside `/api`: it
is a probe for whatever runs the process, not API surface, so ask the service for it directly.
<!-- end section -->
<!-- section: several-services -->

## Several services

This project has {{service-count}} services, each on its own port and each answering the same probe:

{{ports}}
`make demo` starts them all. In the foreground each one is its own terminal, and `PORT` applies to whichever
you start — the targets above set each service's own port as the default.
<!-- end section -->
<!-- section: serves-none -->
## What it serves right now

There is no HTTP transport in this project, so the browser app has nothing to proxy to yet: it runs
and renders, and every `/api` call it makes will fail until a transport is added with `./init --http
<option>`.
<!-- end section -->

<!-- section: driving-browser -->
## Driving it to show something

Reach for the cheapest thing that proves the claim, in this order:

1. **`curl`** for anything the API decides. A status code and a body are the whole claim, and `curl` shows
   both without a browser in the way.
2. **`make test`** for anything a screen renders. A browser app's component tests drive the real component
   with a real user event and no browser at all — see the `react-testing` and `front-end-testing` skills.
3. **A real browser** only when the claim is about the two together: the app calling the service and
   rendering what came back. That is the one thing the levels above cannot prove.

For step 3, Playwright is deliberately **not** a dependency of this project — a browser binary in every
checkout is a cost every contributor pays for something few of them run. Install it when you need it:

```sh
npx --yes playwright install --with-deps chromium   # downloads a browser; --with-deps needs root
npx --yes playwright open {{web-url}}     # or drive it from a script
```

`skills/front-end-testing/resources/playwright-e2e.md` covers what a browser-level test may and may not
claim before you write one. If browser-level tests become part of the suite rather than a one-off, add
Playwright to `{{web-path}}` as a devDependency deliberately, in the same commit as the lockfile change, rather
than leaving every future run to `npx`.
<!-- end section -->
<!-- section: driving-api -->
## Driving it to show something

`curl` is the whole toolkit here: this project has no browser app, so a status code and a body are the
claim. Show the request and the response, not a description of them.
<!-- end section -->

## When it does not come up

- **`make demo` fails at `--wait`.** Something is unhealthy rather than missing. `docker compose --profile
  app logs service` (or `web`) is the answer; the first run installs dependencies inside the container and
  is slow, later runs are not.
- **A port is already taken.** The addresses are pinned rather than negotiated, so that a printed one is
  always the right one. Move a published port in `.env`, which Compose reads, by setting
  {{port-variables}} — never by letting a dev server pick its own and quietly invalidate every URL
  you wrote down.
- **The browser app loads but every call 404s.** The dev server proxies `/api` only. Fetch relative paths —
  `/api/...` — never an absolute `http://localhost:{{service-port}}/...`, which goes straight past the proxy
  and pays a CORS preflight it will fail.
<!-- section: remote-host -->
- **It comes up, but only the machine running it can reach it.** The dev server binds loopback by
  default — right when the browser is on that machine, wrong when it is not: a container, a VM, a remote
  sandbox. Publishing or forwarding the port does not help, because loopback is the boundary it is on the
  far side of. Start it with `make dev-web WEB_HOST=0.0.0.0` and forward the port to that. `make demo`
  already does this for its own `web` container, which is why the container path never needs it.
<!-- end section -->
- **Dependencies look installed but are not.** The containers keep theirs in their own volumes, on purpose:
  a Linux container's `node_modules` in your working tree is how a passing `make verify` starts failing.
  `make demo-down` and `make demo` again rebuilds them.

## What to hand over

`commands/sail.md` sets the shape of a demo stop, and it is not a summary. It opens with the progress
board — ✅ what works now, 🆕 what this slice added, ⬜ what is still to come with the slices counted, ⚠️ what
is not working yet, ➡️ what comes next — and ends with the literal command or URL, the seed data, the result
to expect in the actor's own words, and a direct question about what using it revealed. This skill exists
so that the command is a line you can paste rather than a thing you have to work out again.

**Everything in the table above starts a process that has to still be running when the turn ends.** Start
it, check it answers, and leave it up — in the background, not in a shell you then close. Starting `{{first-command}}`
to prove the command works and stopping it once the proof lands is a test you ran alone: the actor's first
action is opening what you just closed, and a dead port is what they find. Say plainly that it is still
running, and on which address.
