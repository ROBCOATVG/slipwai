PATCH

**A cloud you have not installed no longer takes the language with it.** A language package declares the
targets it has deployment answers for, and every published language names both clouds. The merge used to
refuse any package naming a target this installation had no row for — so installing `python` and no cloud
package left `slipwai list` offering `--language {}`, and `slipwai generate --target none`, which deploys
nowhere and needs no cloud at all, refused outright. All six published languages were unusable until both
cloud packages were installed.

An answer the catalogue cannot reach is now pruned from the backend's row and the rest of the package
merges: `--target` offers what is actually installed, a default pointing at a pruned option goes with it,
and nothing else about the package changes. This is what the keel already did one level up — an option no
installed target offers is dropped, which is why `auth0` sits in `catalog.json` and not in the merged
catalogue until a cloud that offers it arrives — so the two levels now agree.

The pruning is never silent. `slipwai list` names, under each installed language, what it answers that is
out of reach here and the command that shows the targets. An axis the keel does not declare is still a
refusal, because the keel declares every axis there is and one it has not got is a mistake in the package
rather than a gap in what is installed.

**Catch-up:** nothing to do. A project already generated is unaffected; a package that merged before still
merges, and one that was refused for naming an absent cloud now loads with that answer unavailable.
