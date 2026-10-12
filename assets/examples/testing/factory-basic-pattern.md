```typescript
const getMockUser = (overrides?: Partial<User>): User => {
  return UserSchema.parse({
    id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    ...overrides,
  });
};

// Usage
it('creates user with custom email', () => {
  const user = getMockUser({ email: 'custom@example.com' });
  const result = createUser(user);
  expect(result.success).toBe(true);
});
```
