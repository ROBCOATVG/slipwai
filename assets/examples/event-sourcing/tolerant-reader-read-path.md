```typescript
// on read: raw jsonb → validate the stored (possibly old) shape → upcast to current
const toDomainEvent = (raw: unknown): AccountEvent =>
  upcastAccountEvent(StoredAccountEventSchema.parse(raw));
// StoredAccountEventSchema is a tolerant union of explicit persisted versions.
// Unknown fields may be ignored; only fields that were optional or have a proven
// context-invariant default may be absent. parse validates what is on disk, then
// the upcaster maps it to the current shape. parse throws on genuinely corrupt
// data (a bug, not a business case). See event-versioning.md for the upcaster.
```
