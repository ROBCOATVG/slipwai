```typescript
// WRONG — { success: false, error: string } tells you nothing
// Use specific reason literals so the compiler can help
type Result<T> = { success: true; data: T } | { success: false; error: string };
```
