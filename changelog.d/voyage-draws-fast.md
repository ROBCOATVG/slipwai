PATCH

**The Voyage window draws in under a second once warm.** It took thirteen seconds on its own and thirty-eight beside its polls: every request parsed every decision record in every checkout (6,407 parses on manda) and read every slice's benchmark record three times (some 24,000 opens), almost none of which had changed. A file's reading is now kept until the file changes (`file_memo`), so after the first draw the window is drawn from what changed since.

A read of the project past its two seconds is answered at once and made again behind the request, rather than waited on by whichever request found it old: on manda that wait was seven seconds. A person's own action still drops it, so what they did is never answered from before it, and nothing older than a minute is answered.

**Catch-up:** nothing beyond upgrading slipwai.
