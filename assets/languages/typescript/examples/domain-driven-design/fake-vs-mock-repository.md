```typescript
// ✅ Fake — maintains state, implements the real interface
const createFakeRepo = (initial: readonly User[] = []): UserRepository => {
  const store = new Map(initial.map(u => [u.id, u]));
  return {
    findById: async (id) => store.get(id),
    save: async (user) => { store.set(user.id, user); },
  };
};

// ❌ Mock — verifies calls, not behavior
vi.mock('../repositories/user-repository');
```
