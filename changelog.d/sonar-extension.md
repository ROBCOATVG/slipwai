MINOR

**Sonar is available as optional developer tooling.** Adopt it with `./init --extension sonar`, then use
`make sonar` to publish an on-demand analysis to SonarQube or SonarCloud. The remote scan remains outside
`make verify`, keeps its host and token in the environment, uses Maven for Java and `sonar-scanner` for
other languages, and uploads compatible coverage reports when they already exist.

**Catch-up.** After migrating an existing generated repository, install the scanner where needed and run
`./init --extension sonar`; configure `SONAR_HOST_URL` and `SONAR_TOKEN` in each environment that will run
`make sonar`.
