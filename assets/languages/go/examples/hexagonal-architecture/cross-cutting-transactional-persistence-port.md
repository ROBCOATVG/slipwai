```go
package application

import (
	"context"
	"database/sql"
	"errors"

	"gifting/hexagon/domain"
)

// SaveOutcome is the result of an atomic compare-and-save.
type SaveOutcome string

const (
	Saved    SaveOutcome = "saved"
	Conflict SaveOutcome = "conflict"
)

// StoredOccasion pairs an Occasion with the version used for optimistic
// concurrency control.
type StoredOccasion struct {
	Value   domain.Occasion
	Version int
}

// PledgePersistence is the application-owned driven port: one semantic
// operation must save both the occasion and its outbox events, or neither.
type PledgePersistence interface {
	FindOccasionByID(ctx context.Context, id domain.OccasionID) (StoredOccasion, bool, error)
	SaveWithOutbox(ctx context.Context, occasion domain.Occasion, events []domain.PledgeRecorded, expectedVersion int) (SaveOutcome, error)
}

// PostgresPledgePersistence is the driven adapter; it owns the database
// transaction mechanics.
type PostgresPledgePersistence struct {
	DB *sql.DB
}

var _ PledgePersistence = PostgresPledgePersistence{}

func (p PostgresPledgePersistence) FindOccasionByID(ctx context.Context, id domain.OccasionID) (StoredOccasion, bool, error) {
	row := p.DB.QueryRowContext(ctx, `select ... from occasions where id = $1`, id)
	var occasion domain.Occasion
	var version int
	if err := row.Scan( /* ... */ ); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return StoredOccasion{}, false, nil
		}
		return StoredOccasion{}, false, err
	}
	return StoredOccasion{Value: occasion, Version: version}, true, nil
}

func (p PostgresPledgePersistence) SaveWithOutbox(ctx context.Context, occasion domain.Occasion, events []domain.PledgeRecorded, expectedVersion int) (SaveOutcome, error) {
	tx, err := p.DB.BeginTx(ctx, nil)
	if err != nil {
		return "", err
	}
	defer tx.Rollback()

	result, err := tx.ExecContext(ctx,
		`update occasions set version = $2 where id = $1 and version = $3`,
		occasion.ID, expectedVersion+1, expectedVersion)
	if err != nil {
		return "", err
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return "", err
	}
	if rows != 1 {
		return Conflict, nil
	}

	for _, event := range events {
		if _, err := tx.ExecContext(ctx, `insert into outbox (...) values (...)`, event.ID); err != nil {
			return "", err
		}
	}
	if err := tx.Commit(); err != nil {
		return "", err
	}
	return Saved, nil
}
```
