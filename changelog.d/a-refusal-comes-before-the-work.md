PATCH

**`slipwai adopt` refuses an unclean tree, a directory that is not a Git repository, or one already holding a
`project.json` before it surveys anything or asks anything — not after.** The check ran as `adopt` began
writing, which is the right place for it to be enforced but the wrong place to find out: on a repository of
twelve thousand files it meant waiting through the survey, answering the interview, and only then being told
that none of it could be kept. `adopt` still checks when it writes, because it is a library function and that
contract is its own; the command line now checks first as well.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.
