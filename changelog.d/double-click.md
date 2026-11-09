MINOR

**slipwai as an app.** The release carries `Slipwai.app` in a disk image for macOS; the Windows app is built
and held back until projects run on Windows natively. Both are unsigned for now. Opened, the app moves itself to Applications if you agree, keeps the board running each time
you log in, and opens it. A new *This machine* card on Settings shows what the board's routes need here
(Git, Make, Python, Node, and each language's tools), and installs Git, Python or Node only where the
machine has none or only one too old; a good copy is always used as it is. The PRD and codebase pages say at the top when something is missing. The Board tab
says when a newer slipwai is out. The command line is unchanged.

**Fixed:** every standalone executable had shipped without the keel modules that only a language imports,
so it could not load a language.

**Catch-up:** nothing.
