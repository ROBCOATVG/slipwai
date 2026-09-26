PATCH

**`slipwai adopt --confirm` and `--refresh` now re-derive the harness projections, so `make verify` is not red
the moment `/ground` finishes.** Confirming a candidate changes which languages the record names, which
rewrites the skills' prose, which makes every copy under `.claude/skills/` differ from its canonical source —
and `check-agents` fails. Both real adoptions hit it and fixed it by hand with `make agents`. The factory
writes the canonical files, so the factory re-derives what copies them, exactly as `migrate` already does
after a merge. A projector that cannot run is reported rather than raised: the record is written and good
either way.

**And the typecheck the survey proposes for a TypeScript directory with no script of its own now passes
`--skipLibCheck`.** A bare `tsc --noEmit` gave seventeen errors on a real adoption, every one of them inside
`node_modules` where two dependencies ship disagreeing types — nothing the project can fix, and the ratchet
baselines the whole failure as a blanket excuse for the check. With lib types skipped the same tree is green,
and a type error the project actually wrote is what turns it red. A directory with its own `typecheck` script
keeps it, whatever it says.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.
