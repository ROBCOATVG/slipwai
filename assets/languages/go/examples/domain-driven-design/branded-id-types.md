```go
package ddd

import (
	"errors"
	"strings"
)

// OccasionID and GiftIdeaID are distinct types so an ID belonging to one
// entity can never be passed where the other is expected, even though
// both are backed by string.
type OccasionID string
type GiftIdeaID string

func NewOccasionID(raw string) (OccasionID, error) {
	if strings.TrimSpace(raw) == "" {
		return "", errors.New("occasion id cannot be empty")
	}
	return OccasionID(raw), nil
}

func NewGiftIdeaID(raw string) (GiftIdeaID, error) {
	if strings.TrimSpace(raw) == "" {
		return "", errors.New("gift idea id cannot be empty")
	}
	return GiftIdeaID(raw), nil
}
```
