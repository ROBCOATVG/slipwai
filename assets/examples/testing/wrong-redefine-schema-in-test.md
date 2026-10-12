```typescript
// ❌ Schema already defined in src/schemas/user.ts!
const UserSchema = z.object({ ... });
const getMockUser = () => UserSchema.parse({ ... });
```
