MINOR

**Sonar scans now produce coverage on their own optional path.** TypeScript writes LCOV with Vitest,
Python writes coverage.py XML, Java runs tests before its Maven analysis, and Go translates its native
cross-package profile into the exact scope Sonar should count. None of these commands joins or changes
`make verify`, and wrapped applications may still scan without a coverage report.

**Catch-up.** Migrated repositories receive the coverage commands and new ignored report paths. The next
`make sonar` produces fresh reports; no native coverage threshold or required CI check changes.
