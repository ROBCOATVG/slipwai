```typescript
// test/helpers/create-test-db.ts — fresh database per test, no shared state
const createTestDb = async (): Promise<Database> => {
  const db = createDb(':memory:'); // or Testcontainers for real Postgres
  await migrate(db, migrations);
  return db;
};
```
