---
name: run-the-app
description: How to run and demonstrate {{project-name}}. Use when asked to run, start, demo, or screenshot the app, or when a slice reaches its demo checkpoint. This project has no HTTP transport or browser app yet, and this skill says what to demonstrate instead.
---

# Running {{project-name}}

This project has no inbound HTTP transport and no browser app, so there is nothing to start
yet: its entry point is whatever the first slice makes it — a CLI, a worker, a queue consumer. Decide that
before promising a demo, and until then demonstrate through the acceptance tests, which run the same use
cases the eventual entry point will call.

Add a transport later with `./init --http <option>` if the project should serve HTTP after all;
`scripts/backing-services.py --list` shows what this project can still be given.
