```go
func TestOne(t *testing.T) {
	user := newTestUser(t, func(u *User) { u.Name = "Modified User" }) // Fresh state
	_ = user
	// ...
}

func TestTwo(t *testing.T) {
	user := newTestUser(t) // Fresh state, not affected by TestOne

	if user.Name != "Test User" { // ✅ Passes
		t.Fatalf("Name = %q, want %q", user.Name, "Test User")
	}
}
```
