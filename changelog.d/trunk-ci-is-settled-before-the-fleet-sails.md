PATCH

**The board adds the repository you type as `origin` whatever the target, and asks where trunk's CI is
read before the fleet sails.** The harbourmaster refuses every merge it cannot check against the forge, so
a project with no remote built its slices and merged none. Only a target that deploys was ever handed the
repository from the board's form, so for every other target the URL went nowhere. Now it is added as
`origin`, and where none was given, Cast off and Continue the build stop on a card with two answers: add
the remote, or say the project has no CI (`"ci": "off"` in `harbour.json`, merged unverified and said so).

**Catch-up:** none for a project with a remote. Without one, the board asks the next time the fleet is
cast off.
