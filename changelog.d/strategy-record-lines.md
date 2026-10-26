MINOR

**A strategy is decided with the lines its playbook cannot start without, and a modular monolith is a shape, not
a strategy.** Four strategies remain: leave it, in place, strangler fig and rewrite. An accepted ADR that names one
still decides, and now also says which of its required lines it is missing — where a new home lives, the target
shape, the freeze, and for a rewrite its case for one cut-over — and `check-convergence` says so. An ADR that decided
`modular-monolith` reads as a strangler fig whose new home is `inside` and whose target is modules in one deployable.
A system left as it is counts as finished only while its `Review:` date is ahead of it.
