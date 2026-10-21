PATCH

**Several slices testing at once no longer each ask for the whole machine.** A captain with more than one boiler tells every session it starts its share of the cores, `SLIPWAI_TEST_WORKERS` (cores ÷ `boilers`), and the react-vite app's test configuration reads it into vitest's `maxWorkers`; a language package's own test configuration does the same for its deployables. hr-test-2 at three berths on eighteen cores sat at a load of eighty, a 20-second test run took 280, and a guard check that outran the tool timeout was polled with `pgrep vitest` for minutes — which also matched the sibling slice's runs. The implementer's brief now says to wait on its own run and never on a test runner by name. A value a person set already stands.

**Catch-up.** `slipwai migrate` brings the web app's configuration; the service's comes with the TypeScript package's next release.
