PATCH

**The browser app's dev server listens where it is told.** `vite.config.ts` reads its port from the app's own variable — `WEB_PORT`, or `WEB_PORT_<NAME>` for a second app — and is still pinned, with a clash still an error, on the port it was generated with otherwise. Try it is what tells it.
