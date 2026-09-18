MINOR

**Generated repositories can publish Sonar analysis from an optional workflow.** `sonar.yml` is separate
from `verify.yml`, skips scanning unless the extension was adopted and `SONAR_TOKEN` is configured, and
keeps Java on its Maven scanner while other languages use SonarSource's pinned scan action. Remote Sonar
availability therefore cannot change the native verification workflow's result.

**Catch-up.** Migrated generated repositories receive the workflow. Add a `SONAR_TOKEN` repository secret
and a `SONAR_HOST_URL` repository variable to enable it; leaving either unconfigured does not affect
`verify.yml`.
