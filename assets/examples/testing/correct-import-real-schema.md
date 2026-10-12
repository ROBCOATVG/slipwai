```typescript
import { UserSchema } from '@/schemas/user';

const getMockUser = (overrides?: Partial<User>): User => {
  return UserSchema.parse({
    id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    ...overrides,
  });
};
```
