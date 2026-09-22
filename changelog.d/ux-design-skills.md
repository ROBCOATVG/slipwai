MINOR

**A project with a browser app now gets two design skills, and its design page and demo stop tell a slice
when to use them.** The catalogue had 49 skills about how work is done and none about what a screen should
look like or how to check one before it is demonstrated. `frontend-design` (Anthropic's, vendored verbatim at
a pinned commit, Apache-2.0) is the deciding half: ground the design in the subject, plan a compact token
system, review it against the brief for the generic defaults a generated page tends to cluster around, then
build. `web-interface-guidelines` is the checking half: Vercel's Web Interface Guidelines — accessibility,
focus, forms, motion, typography, content handling, the anti-patterns to flag — pinned into the skill as a
file rather than fetched before each review, because a review that needs the network is one that silently
does not happen in a sandbox or a CI runner. Both declare `capabilities: frontend` and ship only where there
is a browser app to design; `docs/design.md`'s *Rules a slice follows* now says to reach for the first before
the first screen and the second before the demo, and the demo stop's styled check names the review as its
second half. Skill counts in the docs are 51.

**Catch-up.** A merge brings both skills whole; `make agents` (or `./init`) re-projects them into every
harness. A project with no browser app receives nothing new.
