# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.0.0

**AWS ships as a target package: `slipwai target install aws`, and `--target aws` is offered.** Everything
a project going to AWS is given is here rather than in the keel — the account stack and the service stack, the
scripts that bootstrap and deploy, the deployment drawing and the production decision record, the tools `./init`
checks for, the parts of the pipeline that are AWS's, and the answers that exist only here.

The keel it is built against names no cloud. That is the whole point of the move: a second place to deploy to is a
package somebody publishes, not a branch somebody adds to `generate`.

**Catch-up:** a project already generated with `--target aws` is unchanged. A keel upgraded past the move needs
`slipwai target install aws` before it will generate another one.

