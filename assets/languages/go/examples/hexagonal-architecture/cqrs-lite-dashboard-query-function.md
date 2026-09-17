```go
package reporting

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

// DashboardRow is the flat, read-optimized shape for the dashboard view.
type DashboardRow struct {
	EventTitle    string
	OccasionEmoji string
	EventDate     time.Time
	SavedAmount   sql.NullInt64
	TargetAmount  int
	RecipientName string
}

// GetDashboardCards is a driven adapter query — not a repository. It joins
// across several aggregates for a read-only dashboard view, deliberately
// bypassing the aggregate-per-repository pattern because this is a display
// read, not a write.
func GetDashboardCards(ctx context.Context, db *sql.DB, userID string) ([]DashboardRow, error) {
	const query = `
		SELECT
			events.title                 AS event_title,
			occasions.emoji              AS occasion_emoji,
			events.event_date            AS event_date,
			savings_goals.saved_amount   AS saved_amount,
			savings_goals.target_amount  AS target_amount,
			recipients.name              AS recipient_name
		FROM events
		INNER JOIN occasions    ON occasions.id = events.occasion_id
		LEFT JOIN savings_goals ON savings_goals.event_id = events.id
		INNER JOIN recipients   ON recipients.id = events.recipient_id
		WHERE events.user_id = $1
	`

	rows, err := db.QueryContext(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("querying dashboard cards: %w", err)
	}
	defer rows.Close()

	var cards []DashboardRow
	for rows.Next() {
		var row DashboardRow
		if err := rows.Scan(
			&row.EventTitle,
			&row.OccasionEmoji,
			&row.EventDate,
			&row.SavedAmount,
			&row.TargetAmount,
			&row.RecipientName,
		); err != nil {
			return nil, fmt.Errorf("scanning dashboard row: %w", err)
		}
		cards = append(cards, row)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterating dashboard rows: %w", err)
	}

	return cards, nil
}
```
