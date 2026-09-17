```go
func newTestUser(overrides ...func(*User)) User {
	u := User{ID: "user-123", Name: "Test User", Email: "test@example.com", Role: "user"} // all required fields present
	for _, override := range overrides {
		override(&u)
	}
	return u
}
```
