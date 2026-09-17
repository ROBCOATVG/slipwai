```go
package queue

import (
	"context"
	"encoding/json"
	"fmt"
)

// HandlePledgeMessage is a queue deployment entrypoint: inline composition +
// driving adapter.
func HandlePledgeMessage(ctx context.Context, message SQSMessage, env Env) error {
	db := openDB(env.DatabaseURL)
	occasionRepo := NewPostgresOccasionRepository(db)
	contributorRepo := NewPostgresContributorRepository(db)
	pledging := NewPledgingToOccasions(occasionRepo, contributorRepo)

	var dto PledgeDTO
	if err := json.Unmarshal([]byte(message.Body), &dto); err != nil {
		return fmt.Errorf("parsing pledge message: %w", err)
	}

	command := dto.ToCommand()
	command.PledgeID = MakePledgeID(message.MessageID)

	_, err := pledging.PledgeToOccasion(ctx, command)
	return err
}
```
