```go
// Repository against a real database — fresh schema per test.
func TestSQLOrderRepository_PersistsAndRetrievesAnOrder(t *testing.T) {
	db := newTestDB(t) // opens a fresh schema and registers t.Cleanup to drop it
	repo := NewSQLOrderRepository(db)
	testOrder := newTestOrder()

	if err := repo.Save(testOrder); err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	found, ok, err := repo.FindByID(testOrder.ID)
	if err != nil {
		t.Fatalf("FindByID() error = %v", err)
	}
	if !ok {
		t.Fatalf("FindByID() found = false, want true")
	}
	if !reflect.DeepEqual(found, testOrder) {
		t.Errorf("FindByID() = %+v, want %+v", found, testOrder)
	}
}
```
