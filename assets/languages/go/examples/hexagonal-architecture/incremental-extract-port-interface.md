```go
package hexagon

import "context"

// user_repository.go — application-owned port

// StoredUser pairs the domain value with its version, for optimistic
// concurrency on save.
type StoredUser struct {
	Value   User
	Version int
}

type SaveOutcome int

const (
	SaveOutcomeSaved SaveOutcome = iota
	SaveOutcomeConflict
)

// UserRepository is a driven port — application-owned because the use case
// consumes it.
type UserRepository interface {
	FindByID(ctx context.Context, id string) (StoredUser, bool, error)
	Save(ctx context.Context, user User, expectedVersion int) (SaveOutcome, error)
}
```
