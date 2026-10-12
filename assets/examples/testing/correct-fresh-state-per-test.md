```typescript
it('test 1', () => {
  const user = getMockUser({ name: 'Modified User' });  // Fresh state
  // ...
});

it('test 2', () => {
  const user = getMockUser();  // Fresh state, not affected by test 1
  expect(user.name).toBe('Test User');  // ✅ Passes
});
```
