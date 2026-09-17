---
description: Check that code and tests implement the event model without semantic drift
argument-hint: [slice-id-or-diff]
---

# Validate code against model

Compare the selected slice with code and tests. Check command and event names, payload schemas, stream
identity, optimistic-concurrency expectations, reads, writes, and projection ownership. Report drift with
both artifact paths and distinguish a code defect from a model decision. Do not silently change either side;
finish by running `make verify` when no decision is outstanding.
