PATCH

**A storyboard on the voyage now shows its styles and its screens when it links `docs/design/`.** The
mock-up stage is told to follow what the project was handed under `docs/design/`, so a storyboard often
links that stylesheet and those drawings, and its specification, by their place on disk
(`../../../docs/design/mockups/styles.css`, `../spec.md`). The board served the storyboard one directory
shallower than it sits, so every one of those links missed: no styles, empty frames. A mock-up is now served
at its own path in the project, under the window's seat (`/mockups/by/<seat>/specs/<feature>/mockups/…`),
and that route also serves the feature's `spec.md` and anything under `docs/design/`. The rest of the
project stays refused. The older `/mockups/<feature>/<name>` addresses still work.

**Catch-up:** none for the project. Restart a running `slipwai bridge --serve` after upgrading.
