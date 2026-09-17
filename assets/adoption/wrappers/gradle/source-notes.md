# Gradle Wrapper, vendored

The four files the Gradle Wrapper is made of, taken from the Gradle repository at its release tag, so that
`slipwai adopt` can write a wrapper into a Gradle repository that has none without a Gradle on the machine to
run `gradle wrapper` — the wrapper is what fetches Gradle. Apache License 2.0 (the scripts carry the SPDX
header; the jar carries the licence in its `META-INF/`).

- Source: https://github.com/gradle/gradle, tag `v9.7.1`, path `gradle/wrapper/` and the two scripts at the root.
- `gradle-wrapper.jar` is kept base64-encoded (`gradle-wrapper.jar.base64`) because every file under
  `assets/` must be text (`tests/test_factory_repository.py` gates it); `slipwai/wrappers.py` decodes it on the
  way out. sha256 of the decoded jar: `7a9ce74cff467ca1bf60a4fcd9f05185acceda4d0f382434d393e17864262c5d`.
- `gradle-wrapper.properties` is the repository's own with `distributionUrl` pointed at the 9.7.1 release
  (the repository's points at the release it builds itself with).

To bump: fetch the four files at the new tag, re-encode the jar, update the URL and this note.
