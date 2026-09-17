```go
// ❌ User already defined in internal/domain/user.go!
type User struct {
	ID    string
	Name  string
	Email string
}

func newTestUser() User {
	return User{ID: "user-123", Name: "Test User", Email: "test@example.com"}
}
```
