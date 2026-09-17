```go
package adapters

import (
	"context"
	"database/sql"
	"errors"
	"sync"
)

// UserRepository is the driven port both adapters below implement.
type UserRepository interface {
	FindByID(ctx context.Context, id string) (User, bool, error)
	Save(ctx context.Context, user User) error
}

// PostgresUserRepository is the driven adapter backed by database/sql.
type PostgresUserRepository struct {
	db *sql.DB
}

func NewPostgresUserRepository(db *sql.DB) *PostgresUserRepository {
	return &PostgresUserRepository{db: db}
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, id string) (User, bool, error) {
	row, err := scanUserRow(r.db.QueryRowContext(ctx, findUserByIDQuery, id))
	if errors.Is(err, sql.ErrNoRows) {
		return User{}, false, nil
	}
	if err != nil {
		return User{}, false, err
	}
	return toUser(row), true, nil
}

func (r *PostgresUserRepository) Save(ctx context.Context, user User) error {
	_, err := r.db.ExecContext(ctx, upsertUserQuery, toRowArgs(user)...)
	return err
}

// FakeUserRepository implements the same port in memory, for use in tests.
type FakeUserRepository struct {
	mu    sync.Mutex
	store map[string]User
}

func NewFakeUserRepository(initial ...User) *FakeUserRepository {
	store := make(map[string]User, len(initial))
	for _, u := range initial {
		store[u.ID] = u
	}
	return &FakeUserRepository{store: store}
}

func (r *FakeUserRepository) FindByID(ctx context.Context, id string) (User, bool, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	u, ok := r.store[id]
	return u, ok, nil
}

func (r *FakeUserRepository) Save(ctx context.Context, user User) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.store[user.ID] = user
	return nil
}
```
