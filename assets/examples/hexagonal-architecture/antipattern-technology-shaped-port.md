```typescript
// ❌ Technology leaks into port
interface UserRepository {
  readonly findBySqlQuery: (sql: string) => Promise<User[]>;
  readonly getFromRedisCache: (key: string) => Promise<User>;
}

// ✅ Business language
interface UserRepository {
  readonly findActive: () => Promise<readonly User[]>;
  readonly findById: (id: UserId) => Promise<User | undefined>;
}
```
