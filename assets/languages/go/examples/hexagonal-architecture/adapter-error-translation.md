```go
package adapters

import (
	"context"
	"database/sql"
)

type CreateUserOutcome int

const (
	UserCreated CreateUserOutcome = iota
	UserAlreadyExists
)

type CreateUserResult struct {
	Outcome CreateUserOutcome
}

type UserCreator interface {
	Create(ctx context.Context, user User) (CreateUserResult, error)
}

// PostgresUserCreator translates an expected storage condition into port
// vocabulary. Unexpected infrastructure errors (connection lost, disk full)
// propagate unchanged.
type PostgresUserCreator struct {
	db *sql.DB
}

func NewPostgresUserCreator(db *sql.DB) *PostgresUserCreator {
	return &PostgresUserCreator{db: db}
}

func (c *PostgresUserCreator) Create(ctx context.Context, user User) (CreateUserResult, error) {
	_, err := c.db.ExecContext(ctx, insertUserQuery, toRowArgs(user)...)
	switch {
	case err == nil:
		return CreateUserResult{Outcome: UserCreated}, nil
	case isUniqueConstraintError(err):
		return CreateUserResult{Outcome: UserAlreadyExists}, nil
	default:
		return CreateUserResult{}, err // unexpected: connection lost, disk full, ...
	}
}
```
