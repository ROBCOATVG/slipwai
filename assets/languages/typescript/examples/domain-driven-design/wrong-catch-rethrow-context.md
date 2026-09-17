```typescript
// WRONG — wrapping exceptions adds noise, not clarity
try { ... } catch (e) { throw new PledgeError('Failed to pledge', { cause: e }); }
```
