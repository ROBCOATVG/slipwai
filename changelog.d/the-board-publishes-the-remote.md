PATCH

**The board creates the repository it was given and pushes the project there.** For a target that deploys
nothing, the repository typed on the board was only added as `origin`: nothing created it on GitHub and
nothing pushed, so the fleet's first merge was refused against a forge with no such repository. Now, once
`./init`'s work is committed, the board creates the repository where it is missing — private, as the cloud
targets' bootstrap does — and pushes `main`. *Add the remote* on the Voyage page does the same at once.
What cannot be done (no `gh`, no rights to create it) is said on the card, and the project is made anyway.

**Catch-up:** a project given a remote that does not exist yet: `gh repo create <owner/name> --private`,
then `git push -u origin main`.
