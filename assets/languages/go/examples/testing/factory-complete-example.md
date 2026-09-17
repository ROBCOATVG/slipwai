```go
import "myapp/internal/domain" // Import real validation

func newTestUser(t *testing.T, overrides ...func(*domain.User)) domain.User {
	t.Helper()
	u := domain.User{
		ID:        "user-123",
		Name:      "Test User",
		Email:     "test@example.com",
		Role:      "user",
		IsActive:  true,
		CreatedAt: time.Date(2024, time.January, 1, 0, 0, 0, 0, time.UTC),
	}
	for _, override := range overrides {
		override(&u)
	}
	if err := u.Validate(); err != nil {
		t.Fatalf("invalid test fixture: %v", err)
	}
	return u
}
```
