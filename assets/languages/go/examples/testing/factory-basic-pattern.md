```go
func newTestUser(t *testing.T, overrides ...func(*User)) User {
	t.Helper()
	u := User{ID: "user-123", Name: "Test User", Email: "test@example.com", Role: "user"}
	for _, override := range overrides {
		override(&u)
	}
	if err := u.Validate(); err != nil {
		t.Fatalf("invalid test fixture: %v", err)
	}
	return u
}

// Usage
func TestCreateUser_WithCustomEmail(t *testing.T) {
	user := newTestUser(t, func(u *User) { u.Email = "custom@example.com" })

	result := CreateUser(user)

	if !result.Success {
		t.Fatalf("expected success, got error: %q", result.Error)
	}
}
```
