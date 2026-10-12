MINOR

**Azure ships as a target package: `slipwai target install azure`, and `--target azure` is offered.** Everything
a project going to Azure is given is here rather than in the keel — the account stack and the service stack, the
scripts that bootstrap and deploy, the deployment drawing and the production decision record, the tools `./init`
checks for, the parts of the pipeline that are Azure's, and the answers that exist only here.

The keel it is built against names no cloud. That is the whole point of the move: a second place to deploy to is a
package somebody publishes, not a branch somebody adds to `generate`.

**Catch-up:** a project already generated with `--target azure` is unchanged. A keel upgraded past the move needs
`slipwai target install azure` before it will generate another one.
