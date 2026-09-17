```go
package ddd

import "context"

type OccasionID string

type Occasion struct {
	ID   OccasionID
	Name string
}

// OccasionRepository is an application-owned repository contract -- an
// inside-owned port when hexagonal architecture is used. The bool return
// on FindByID reports whether an Occasion with that ID exists, separately
// from any infrastructure error.
type OccasionRepository interface {
	FindByID(ctx context.Context, id OccasionID) (occasion Occasion, found bool, err error)
	Save(ctx context.Context, occasion Occasion) error
}

// Concrete implementations belong with infrastructure/integration; in
// hexagonal architecture they are driven adapters.
```
