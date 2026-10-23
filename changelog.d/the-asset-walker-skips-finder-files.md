PATCH

**A Finder `.DS_Store` in the keel's `assets/` no longer breaks `generate`.** The walker every reader of the asset trees goes through already left out Python's `__pycache__`; a macOS checkout that has been opened in a Finder window carries a binary `.DS_Store` beside the toolkit's scripts, and reading it as text stopped `generate`, the conformance suite and fifty of the keel's own tests with a `UnicodeDecodeError`. It is left out the same way.

**Catch-up:** nothing. This is the keel's own tree and reaches no generated project.
