```typescript
// packages/billing/adapters/driven/postgres/src/drizzle-user-repository.ts — driven adapter
const createDrizzleUserRepository = (db: Database): UserRepository => ({
  findById: async (id) => {
    const row = await db.select().from(users).where(eq(users.id, id)).get();
    return row ? { value: toUser(row), version: row.version } : undefined;
  },
  save: async (user, expectedVersion) => {
    const updated = await db.update(users)
      .set({ ...toRow(user), version: expectedVersion + 1 })
      .where(and(eq(users.id, user.id), eq(users.version, expectedVersion)))
      .returning({ id: users.id });
    return updated.length === 1 ? 'saved' : 'conflict';
  },
});
```
