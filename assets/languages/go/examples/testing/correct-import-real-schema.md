```go
import "myapp/internal/domain"

func newTestUser(t *testing.T, overrides ...func(*domain.User)) domain.User {
	t.Helper()
	u := domain.User{ID: "user-123", Name: "Test User", Email: "test@example.com"}
	for _, override := range overrides {
		override(&u)
	}
	return u
}
```
