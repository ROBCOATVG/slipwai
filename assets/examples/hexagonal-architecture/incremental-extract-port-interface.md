```typescript
// packages/billing/hexagon/application/src/user-repository.ts — application-owned port
type StoredUser = { readonly value: User; readonly version: number };

interface UserRepository {
  readonly findById: (id: UserId) => Promise<StoredUser | undefined>;
  readonly save: (user: User, expectedVersion: number) => Promise<'saved' | 'conflict'>;
}
```
