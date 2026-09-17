```go
package queries

import (
	"context"
	"database/sql"
	"errors"
)

// ParticipantEventView is a read-optimized DTO, not a domain aggregate.
type ParticipantEventView struct {
	EventID      string
	EventName    string
	OccasionName string
	ClaimedBy    sql.NullString
}

// GetParticipantEventView is a query function that JOINs across aggregates
// for a read-only display view. It lives at
// reporting/adapters/driven/postgres/queries/, outside the repository
// pattern, and returns a DTO rather than a domain aggregate.
func GetParticipantEventView(ctx context.Context, db *sql.DB, eventID string) (ParticipantEventView, bool, error) {
	const query = `
		SELECT e.id, e.name, o.name, g.claimed_by
		FROM events e
		INNER JOIN occasions o ON o.id = e.occasion_id
		LEFT JOIN gift_claims g ON g.event_id = e.id
		WHERE e.id = $1
	`
	var view ParticipantEventView
	err := db.QueryRowContext(ctx, query, eventID).Scan(
		&view.EventID, &view.EventName, &view.OccasionName, &view.ClaimedBy,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return ParticipantEventView{}, false, nil
	}
	if err != nil {
		return ParticipantEventView{}, false, err
	}
	return view, true, nil
}
```
