MINOR

**A guard can be told when its extension's own tools are used.** A guard that must refuse *until this
session has asked the index* could not know that a session had asked: an ask over MCP is a tool call that
reached no guard. A guard can now declare `"sees": ["mcp__<server>__.*"]`, and slipwai runs it with
`SLIPWAI_POINT=tool-use` and a small JSON event on stdin when one of those tools is about to be used. The
guard is told which tool and whose call, never the call's arguments, and it cannot refuse there: the exit
code is discarded. `sees` is limited to one MCP server's tools per entry and 8 entries, so no extension can
put a guard in front of every tool call. On Claude Code the matcher for it is written into
`.claude/settings.json` from the guards a person agreed to.

**Catch-up:** `slipwai migrate` brings the scripts; nothing else for a project whose guards declare no
`sees`. An extension author adds `sees` to the guard in `extension.json`; a project that already agreed to
that guard is told it changed and agrees again with `python3 scripts/extensions/guards.py --elect <key>`.
