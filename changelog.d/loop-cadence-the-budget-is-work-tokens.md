MINOR

**A stage's token budget counts the work, and the benchmark reads it at every bracket.** `harbour.json`'s
`tokens`, `bunker_per_slice` and `bunker_per_day` were thousands of input tokens, and on a host whose context
is re-read every turn that measured the context and not the work: one 81-minute implement pass recorded
19.67M input against a 1,200k budget, 19.43M of it cache reads, and the console then added the cache reads
again and said 39.1M. The unit is now **work tokens** — uncached input plus output — on every harness:
`scripts/agents/benchmark.py` normalises a Codex read, whose `input_tokens` includes its cache reads, so
`input` means the uncached part as it already did on Claude Code, and reads an older Codex record the same way.
`benchmark.py start` prints the stage's budget and what the slice has spent of its bunker; `end` says *over
budget* on stderr and writes it on the entry when the stage passed either number; the summary line carries
`work` beside `in` and `out`. The *When a stage reaches its budget* section says the lines are the control
under `/sail`, where no captain is ending stages by their silence.

**Catch-up:** `slipwai migrate` brings the script and the section. The numbers in `harbour.json` are not
changed; they were sized for input and are now generous for work, so a project that wants the old pressure
lowers them, and `slipwai telegraph` says what they mean.
