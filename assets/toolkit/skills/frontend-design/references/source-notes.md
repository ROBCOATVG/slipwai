# Source Notes

`SKILL.md` was vendored on 22 September 2026 from Anthropic's
[`frontend-design` at `41bbe19`](https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/frontend-design)
(`skills/frontend-design/SKILL.md`, last changed upstream on 3 September 2026), under the Apache License 2.0
that upstream ships beside it as `LICENSE.txt` and this directory carries as `LICENSE`.

The body is upstream's, unchanged. Local departures are confined to the front matter and one paragraph:

- `license:` names `LICENSE` rather than `LICENSE.txt`, because that is the file name every vendored skill
  in this catalogue uses and the one `tests/test_code_index.py` recognises;
- `capabilities: frontend` is added, so the skill ships only to a project with a browser app
  (see `docs/skills.md` in the factory);
- a blockquote under the title records the provenance and says where this repository already keeps the
  decisions the skill asks for — `docs/design.md` and the browser app's `tokens.css` — so the two-pass
  plan the skill describes lands in the files a slice is already told to read and change.

To refresh: fetch upstream's `SKILL.md` at the new commit, reapply the three departures above, update the
pin here and in `REFERENCES.md`, and re-read `LICENSE.txt` in case the terms moved.
