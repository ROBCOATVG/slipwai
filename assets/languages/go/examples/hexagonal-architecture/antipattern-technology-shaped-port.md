```go
// ❌ Technology leaks into the port
type UserRepository interface {
	FindBySQLQuery(ctx context.Context, query string) ([]User, error)
	GetFromRedisCache(ctx context.Context, key string) (User, error)
}

// ✅ Business language
type UserRepository interface {
	FindActive(ctx context.Context) ([]User, error)
	FindByID(ctx context.Context, id string) (User, bool, error)
}
```
