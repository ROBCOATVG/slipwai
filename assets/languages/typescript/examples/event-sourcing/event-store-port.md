```typescript
// port (application layer) — owned by the command handler that consumes it.
// Typed to one aggregate's event family, like a repository (the underlying
// adapter can hold many streams; it parses stored JSON into E on read).
interface EventStore<E> {
  readonly readStream: (streamId: StreamId) => Promise<{ readonly events: readonly E[]; readonly version: number }>;
  readonly appendToStream: (
    streamId: StreamId,
    events: readonly E[],
    options: { readonly expectedVersion: number },
  ) => Promise<'ok' | 'version-conflict'>;
}
```
