# Source Notes

`references/guidelines.md` is `command.md` from Vercel Labs'
[`web-interface-guidelines` at `e3d624b`](https://github.com/vercel-labs/web-interface-guidelines/blob/e3d624baaf29dc1fc645aff3e38f03e564d2d6b1/command.md)
(last changed upstream on 18 August 2026), copied unchanged on 22 September 2026. Upstream's MIT notice is
preserved as `LICENSE`.

`SKILL.md` is original to this repository. Vercel Labs also publishes a `web-design-guidelines` skill in
[`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills/tree/ba46938889d4e58635362fb8f618e1178ac3ec46/skills/web-design-guidelines)
whose whole instruction is to fetch `command.md` from GitHub before each review. It was not copied, for two
reasons: a review that needs the network is a review that silently does not happen in a sandbox or a CI
runner, and that repository carries no licence file at the commit inspected. The rules themselves are the
value, and they are MIT.

Local departures from upstream's use of the rules:

- the rules are read from disk, never fetched;
- the review is scoped to the files a slice changed, because that is what the demo stop asks for;
- `docs/design.md` wins where it and the rules disagree, and the one known disagreement (heading case) is
  named so it is not raised on every review;
- findings are fixed before the demo rather than reported and left.

To refresh: fetch `command.md` at the new commit into `references/guidelines.md`, update the pin here and
in `REFERENCES.md`, and re-read the upstream `LICENSE`.
