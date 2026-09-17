```typescript
save: async (occasion): Promise<'saved' | 'conflict'> => {
  const updated = await db.update(occasions)
    .set({ ...toRow(occasion), version: occasion.version + 1 })
    .where(and(eq(occasions.id, occasion.id), eq(occasions.version, occasion.version)));
  return updated.rowsAffected === 1 ? 'saved' : 'conflict';
},
```
