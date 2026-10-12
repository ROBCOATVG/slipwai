```typescript
type CreateUserResult =
  | { readonly success: true }
  | { readonly success: false; readonly reason: 'already-exists' };

// Driven adapter: translate an expected storage condition into port vocabulary
const createDrizzleUserCreator = (db: Database) => ({
  create: async (user: User): Promise<CreateUserResult> => {
    try {
      await db.insert(users).values(toRow(user));
      return { success: true };
    } catch (e) {
      if (isUniqueConstraintError(e)) {
        return { success: false, reason: 'already-exists' };
      }
      throw e; // unexpected errors (connection lost, disk full) propagate
    }
  },
});
```
