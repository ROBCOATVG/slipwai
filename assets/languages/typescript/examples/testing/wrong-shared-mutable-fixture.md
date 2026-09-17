```typescript
const user: User = { id: 'user-123', name: 'Test User', ... };

it('test 1', () => {
  user.name = 'Modified User';
});

it('test 2', () => {
  expect(user.name).toBe('Test User');  // Order-dependent failure
});
```
