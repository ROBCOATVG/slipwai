```go
package ddd

import (
	"context"
	"database/sql"
)

type SaveOutcome int

const (
	SaveSaved SaveOutcome = iota
	SaveConflict
)

// Save does a compare-and-swap on the version field: the WHERE clause only
// matches the row if nobody else has saved a newer version in the meantime.
func Save(ctx context.Context, db *sql.DB, occasion Occasion) (SaveOutcome, error) {
	result, err := db.ExecContext(ctx,
		`UPDATE occasions SET name = $1, budget_minor_units = $2, version = $3
		 WHERE id = $4 AND version = $5`,
		occasion.Name, occasion.Budget.MinorUnits, occasion.Version+1,
		occasion.ID, occasion.Version,
	)
	if err != nil {
		return 0, err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return 0, err
	}
	if rows == 1 {
		return SaveSaved, nil
	}
	return SaveConflict, nil
}
```
