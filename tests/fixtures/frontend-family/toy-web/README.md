# toy-web

A test fixture, and the smallest **frontend-only** package slipwai loads: the family `toy-web`, no backend, and
one browser app, `toy-vite`, under `assets/frontends/toy-vite/` in the layout slipwai reads by name. Every file
is a placeholder. `tests/test_frontend_only.py` generates the toy's backend beside it, which is the proof a
package may ship browser apps alone and be combined with a backend-only one. See `docs/frontend-protocol.md`.
