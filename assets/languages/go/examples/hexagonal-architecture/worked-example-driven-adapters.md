```go
// gifting/adapters/driven/postgres/pledge_persistence.go
package postgres

import (
	"context"
	"database/sql"
	"errors"

	"gifting/hexagon/application"
	"gifting/hexagon/domain"
)

// PledgePersistence is the concrete application.PledgePersistence backed by
// Postgres. It translates between domain types and rows and implements the
// atomic compare-and-save-with-outbox contract in one transaction.
type PledgePersistence struct {
	DB *sql.DB
}

var _ application.PledgePersistence = PledgePersistence{}

func (p PledgePersistence) FindOccasionByID(ctx context.Context, id domain.OccasionID) (application.StoredOccasion, bool, error) {
	row := p.DB.QueryRowContext(ctx, `
		select name, budget_minor_units, budget_currency,
		       total_pledged_minor_units, total_pledged_currency,
		       is_funding_closed, version
		from occasions where id = $1`, id)

	occasion := domain.Occasion{ID: id}
	var version int
	err := row.Scan(
		&occasion.Name, &occasion.Budget.MinorUnits, &occasion.Budget.Currency,
		&occasion.TotalPledged.MinorUnits, &occasion.TotalPledged.Currency,
		&occasion.IsFundingClosed, &version,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return application.StoredOccasion{}, false, nil
	}
	if err != nil {
		return application.StoredOccasion{}, false, err
	}
	return application.StoredOccasion{Value: occasion, Version: version}, true, nil
}

func (p PledgePersistence) SaveWithOutbox(ctx context.Context, occasion domain.Occasion, events []domain.PledgeRecorded, expectedVersion int) (application.SaveOutcome, error) {
	tx, err := p.DB.BeginTx(ctx, nil)
	if err != nil {
		return "", err
	}
	defer tx.Rollback()

	// The version predicate prevents two readers from overwriting each
	// other; a conflict inserts no outbox row.
	result, err := tx.ExecContext(ctx, `
		update occasions
		set name = $2, budget_minor_units = $3, budget_currency = $4,
		    total_pledged_minor_units = $5, total_pledged_currency = $6,
		    is_funding_closed = $7, version = $8
		where id = $1 and version = $9`,
		occasion.ID, occasion.Name, occasion.Budget.MinorUnits, occasion.Budget.Currency,
		occasion.TotalPledged.MinorUnits, occasion.TotalPledged.Currency,
		occasion.IsFundingClosed, expectedVersion+1, expectedVersion)
	if err != nil {
		return "", err
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return "", err
	}
	if rows != 1 {
		return application.Conflict, nil
	}

	for _, event := range events {
		if _, err := tx.ExecContext(ctx, `
			insert into outbox (event_id, occasion_id, contributor_id, amount_minor_units, amount_currency)
			values ($1, $2, $3, $4, $5)`,
			event.ID, event.OccasionID, event.ContributorID, event.Amount.MinorUnits, event.Amount.Currency); err != nil {
			return "", err
		}
	}

	if err := tx.Commit(); err != nil {
		return "", err
	}
	return application.Saved, nil
}

// gifting/adapters/driven/postgres/pledge_projection.go

// PledgeProjection is the concrete application.PledgeProjection. It inserts
// on the event's unique ID and no-ops on conflict, so redelivery is
// idempotent and an existing projection is never overwritten with incoming
// data.
type PledgeProjection struct {
	DB *sql.DB
}

var _ application.PledgeProjection = PledgeProjection{}

func (p PledgeProjection) RecordFrom(ctx context.Context, event domain.PledgeRecorded) error {
	_, err := p.DB.ExecContext(ctx, `
		insert into pledge_projection (event_id, occasion_id, contributor_id, amount_minor_units, amount_currency)
		values ($1, $2, $3, $4, $5)
		on conflict (event_id) do nothing`,
		event.ID, event.OccasionID, event.ContributorID, event.Amount.MinorUnits, event.Amount.Currency)
	return err
}
```
