PATCH

**A bosun's decision entry passes the gate it was written for.** `commands/cruise.md` tells `drive-bosun` to
record every workaround as a decision entry with `Decided by: drive-bosun`, and `scripts/check-decisions.py`
accepted only the host, the skipper and a human — so the first run that needed the bosun left `make verify`
failing on the entry the bosun was told to write. The gate and the record template now name the bosun, alone
or with its model, beside the other four.

**Catch-up.** `slipwai migrate` brings the gate and the command text; an entry already written as
`drive-bosun` passes as it stands.
