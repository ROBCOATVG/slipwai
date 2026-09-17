```go
// ❌ Domain imports database/sql directly
import "database/sql"

func FindActiveUsers(db *sql.DB) ([]User, error) {
	rows, err := db.Query(`SELECT id, email, name FROM users WHERE active = true`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanUsers(rows)
}

// ✅ Application defines the port it consumes; an adapter implements it
type UserRepository interface {
	FindActive(ctx context.Context) ([]User, error)
}
```
