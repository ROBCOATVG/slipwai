```typescript
// ❌ Domain imports Drizzle
import { eq } from 'drizzle-orm';
export const findActiveUsers = async (db) => db.select()...

// ✅ Application defines the contract it consumes; adapter implements it
interface UserRepository {
  readonly findActive: () => Promise<readonly User[]>;
}
```
