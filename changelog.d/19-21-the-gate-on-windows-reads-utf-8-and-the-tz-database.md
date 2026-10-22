PATCH

**On Windows, git output is read as UTF-8, a session's result line is decoded before it is parsed, and
the session-limit reset is placed in its named zone.** A decisions heading's em dash and a quickstart's
title came back as mojibake from `git show` decoded in the console's code page, so sibling branches' decision
numbers were handed out twice and the Try it card lost its titles. A result line with one byte in the
console's encoding was dropped whole by `json.loads`, so a refusal to run read as three failed runs. And
`zoneinfo` has no database on Windows, so `resets 9:40pm (Europe/London)` paused an hour out: the gate's
tooling now carries `tzdata`. The captain's output is read with its `\r\n` folded, and the timeline's day
tick no longer uses a glibc-only `strftime` flag.
