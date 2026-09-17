```go
// newTestDB returns a fresh, isolated database per test — no shared
// state leaks between tests — and registers its own cleanup.
func newTestDB(t *testing.T) *sql.DB {
	t.Helper()

	db, err := sql.Open("sqlite3", ":memory:") // or Testcontainers for real Postgres
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Errorf("close test db: %v", err)
		}
	})

	if err := applyMigrations(db, migrations); err != nil {
		t.Fatalf("apply migrations: %v", err)
	}
	return db
}
```
