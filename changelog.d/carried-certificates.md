PATCH

**The app verifies HTTPS on a new Windows.** On a Windows nobody had browsed on yet, every fetch the board
made failed with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`: the language index
could not be read, Node could not be installed, and with no Node the settings page said *nothing this
machine can launch yet*. Windows fetches most of its certificate roots only when a Windows program first
needs one, and Python does not ask. The app and the executable now carry Mozilla's roots (the `certifi`
package, pinned in the build) and trust them beside the machine's own, so a root an organisation installed
for its proxy still counts. A keel installed with pip is unchanged and has no new dependency.

**Catch-up:** nothing; install the new build.
