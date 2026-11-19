PATCH

**`slipwai hooks` says where a point's script is not in the package.** `extension list` and `extension check`
have said "not in the package, so it never runs" of a declared hook whose file the package does not ship;
`slipwai hooks` still listed that extension on the point as though it ran. It now names the script beside the
extension, in the same words, so the two listings cannot be read as disagreeing.

**Catch-up:** nothing; it is what a listing prints. Where it names a script, install a release of that
extension that ships it: `slipwai extension install <key>`.
