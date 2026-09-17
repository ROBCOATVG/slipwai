```typescript
// port (application layer) — owned by the command handler that consumes it.
// Typed to one aggregate's event family E (like a repository). One physical
// store holds many stream types; the adapter parses stored JSON into E on read,
// so each typed EventStore<E> is a view over the streams of that family.
interface EventStore<E> {
  readonly readStream: (
    streamId: StreamId,
  ) => Promise<{ readonly events: readonly E[]; readonly version: number }>;

  readonly appendToStream: (
    streamId: StreamId,
    events: readonly E[],
    options: { readonly expectedVersion: number },
  ) => Promise<'ok' | 'version-conflict'>;
}
```
