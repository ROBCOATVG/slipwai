# Maintainer skills

Five skills for somebody extending slipwai itself, as against somebody using it. `make skills` copies
these and the toolkit's into `.claude/skills/` for this checkout's own sessions; that directory is
generated and ignored by git, so edit these and run `make skills`.

| Skill | For |
| --- | --- |
| `add-module` | Publishing a language package: services, browser apps or both, from deciding which to releasing |
| `add-framework` | Adding a framework (a backend) to a family somebody already published |
| `add-extension` | Publishing an extension: optional dev tooling a project elects at `./init` |
| `add-target` | Adding somewhere a project can be deployed to |
| `add-backing-service` | Adding an answer to an axis — where events live, who authenticates |

**None of them describes a step a verb already does.** Where `slipwai package new` writes a file, the skill
says so and moves on. A skill that repeated the scaffold would be a second copy of it, and the second copy
is the one that goes stale.
