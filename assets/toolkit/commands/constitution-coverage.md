---
description: Check or print the principles this project's constitution must carry
argument-hint: [--requirements] [requirement-key ...]
---

# Constitution coverage

`.specify/memory/constitution.md` is what every later phase treats as the authority, so a principle
dropped from it is a gate that silently stopped existing. `scripts/check-constitution.py` states the floor:
{{scope}}

```sh
make check-constitution                                # what is missing, if anything
python3 scripts/check-constitution.py --requirements   # the normative text for every requirement
python3 scripts/check-constitution.py --requirements trunk-based-integration governance
```

Run the check with no arguments. With `--requirements`, print the normative text instead — that is the
drafting path, and passing requirement keys narrows it to the ones a finding named.

Amend the constitution rather than the gate, and rephrase freely: the check reads for the terms an
obligation cannot be written without, not for one wording. Where a finding needs a decision nobody has
made — the domain invariant, a retention period, a compliance scope, an unfilled `[PLACEHOLDER]` — report
which requirement is unmet and ask. An invented obligation reads as ratified afterwards, which is worse
than an open question.
