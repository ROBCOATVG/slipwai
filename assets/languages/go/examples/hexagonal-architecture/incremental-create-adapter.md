```go
package adapters

import (
	"context"
	"database/sql"
	"errors"
)

// postgres_user_repository.go — driven adapter

// PostgresUserRepository is the driven adapter backed by database/sql, using
// optimistic concurrency (a version column) on save.
type PostgresUserRepository struct {
	db *sql.DB
}

func NewPostgresUserRepository(db *sql.DB) *PostgresUserRepository {
	return &PostgresUserRepository{db: db}
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, id string) (StoredUser, bool, error) {
	var row userRow
	err := r.db.QueryRowContext(ctx,
		`SELECT id, balance_minor_units, currency, version FROM users WHERE id = $1`, id,
	).Scan(&row.ID, &row.BalanceMinorUnits, &row.Currency, &row.Version)
	if errors.Is(err, sql.ErrNoRows) {
		return StoredUser{}, false, nil
	}
	if err != nil {
		return StoredUser{}, false, err
	}
	return StoredUser{Value: toUser(row), Version: row.Version}, true, nil
}

func (r *PostgresUserRepository) Save(ctx context.Context, user User, expectedVersion int) (SaveOutcome, error) {
	result, err := r.db.ExecContext(ctx,
		`UPDATE users SET balance_minor_units = $1, currency = $2, version = $3
		 WHERE id = $4 AND version = $5`,
		user.Balance.MinorUnits, user.Balance.Currency, expectedVersion+1, user.ID, expectedVersion,
	)
	if err != nil {
		return 0, err
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return 0, err
	}
	if rows == 1 {
		return SaveOutcomeSaved, nil
	}
	return SaveOutcomeConflict, nil
}

type userRow struct {
	ID                string
	BalanceMinorUnits int64
	Currency          string
	Version           int
}

func toUser(row userRow) User {
	return User{ID: row.ID, Balance: Money{MinorUnits: row.BalanceMinorUnits, Currency: row.Currency}}
}
```
