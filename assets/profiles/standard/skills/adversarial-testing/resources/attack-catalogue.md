# Attack catalogue

Choose probes based on the promises and seams present in the slice. This is a source of hypotheses, not a
checklist; every reported finding must name the violated contract and observable consequence.

## Boundary parsing

- Omit required fields; add unknown ones; supply null, wrong types, oversized strings, invalid Unicode,
  duplicate keys, deep nesting, and values exactly at either side of a limit.
- Try numeric overflow, precision loss, negative and zero boundary values, malformed timestamps, and
  unsupported content types or encodings.
- Supply actor, account, or tenant identifiers that conflict with the authenticated identity.
- Confirm malformed input produces a stable client response without stack traces or internal details.

## Authentication, authorization, and tenancy

- Exercise each entry point anonymously, with expired credentials, with insufficient privileges, and as a
  different tenant or subject.
- Look for a second entry point that bypasses a check applied only in one adapter.
- Guess identifiers and compare not-found/forbidden responses, timing, counts, and pagination metadata for
  existence leaks.
- Check bulk, export, search, realtime, and background paths as well as ordinary item routes.

## Idempotency and retries

- Repeat the same request sequentially and concurrently; then reuse its idempotency key with different
  content.
- Lose the response after the operation succeeds and retry from the caller's perspective.
- Retry after a transient failure and verify a cached failure does not become permanent accidentally.
- Replay webhook or queue deliveries using both the same provider identifier and equivalent content under a
  new identifier.

## Concurrency and state transitions

- Race two individually valid operations whose combined result could violate an invariant.
- Submit updates from stale versions, cancel during completion, and repeat terminal transitions.
- Vary interleavings around reads, writes, cache invalidation, and side effects.
- Apply sustained contention and verify retries are bounded and failure is observable.

## Time and ordering

- Test exactly on expiry boundaries, clock movement backwards, equal timestamps, daylight-saving changes,
  and non-UTC inputs.
- Confirm ordering does not rely on wall-clock timestamps when ties or skew are possible.
- Check timeout and retry budgets agree across nested calls and cannot amplify load indefinitely.

## Driven dependency failure

- Make each dependency unavailable, slow, malformed, or successful only after the caller gives up.
- Interrupt the process before and after each durable write or external side effect.
- Exhaust connection/thread pools and verify backpressure, cancellation, and recovery.
- Confirm failures do not leak credentials, provider messages, queries, or internal identifiers.

## Data integrity and evolution

- Read data produced by the previous deployed schema and tolerate additive fields where the contract permits.
- Interrupt or rerun migrations and test rolling deployment with old and new application versions overlapping.
- Compare cache/index/view state with the authoritative transactional data after failure and recovery.
- Exercise duplicate, missing, and out-of-order messages where asynchronous delivery exists.

## Privacy and operational surface

- Inspect logs, metrics, traces, exports, backups, and error responses for personal or secret data.
- Verify erasure and retention behaviour across derived stores and external providers.
- Start with required configuration missing, empty, malformed, or mutually inconsistent.
- Confirm a failing background job is distinguishable from an idle one and correlation survives every hop.
- Ask whether each promised detection signal would actually alert, rather than merely existing on a dashboard.
