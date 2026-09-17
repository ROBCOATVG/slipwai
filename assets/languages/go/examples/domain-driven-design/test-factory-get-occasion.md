```go
package ddd

import "testing"

type Currency string

type Money struct {
	MinorUnits int64
	Currency   Currency
}

type OccasionID string
type GiftIdeaID string

type GiftIdea struct {
	ID          GiftIdeaID
	Description string
}

type Occasion struct {
	ID              OccasionID
	Name            string
	GiftIdeas       []GiftIdea
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

// OccasionOption overrides a single field of the default test Occasion
// built by NewTestOccasion -- Go's equivalent of a partial-overrides
// object, since there is no structural spread.
type OccasionOption func(*Occasion)

func WithName(name string) OccasionOption {
	return func(o *Occasion) { o.Name = name }
}

func WithFundingClosed(closed bool) OccasionOption {
	return func(o *Occasion) { o.IsFundingClosed = closed }
}

func WithTotalPledged(amount Money) OccasionOption {
	return func(o *Occasion) { o.TotalPledged = amount }
}

// NewTestOccasion is a test data factory building a default, valid
// Occasion; pass Option functions to override individual fields.
func NewTestOccasion(opts ...OccasionOption) Occasion {
	occasion := Occasion{
		ID:              OccasionID("occasion-1"),
		Name:            "Mum's Birthday",
		Budget:          Money{MinorUnits: 10_000, Currency: "GBP"},
		TotalPledged:    Money{MinorUnits: 0, Currency: "GBP"},
		IsFundingClosed: false,
	}
	for _, opt := range opts {
		opt(&occasion)
	}
	return occasion
}

func TestNewTestOccasion(t *testing.T) {
	tests := []struct {
		name string
		opts []OccasionOption
		want Occasion
	}{
		{
			name: "defaults",
			opts: nil,
			want: NewTestOccasion(),
		},
		{
			name: "funding closed override",
			opts: []OccasionOption{WithFundingClosed(true)},
			want: Occasion{
				ID:              OccasionID("occasion-1"),
				Name:            "Mum's Birthday",
				Budget:          Money{MinorUnits: 10_000, Currency: "GBP"},
				TotalPledged:    Money{MinorUnits: 0, Currency: "GBP"},
				IsFundingClosed: true,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := NewTestOccasion(tt.opts...)
			// GiftIdeas is a slice, so Occasion is not comparable with ==;
			// compare the fields this test actually varies.
			if got.Name != tt.want.Name || got.Budget != tt.want.Budget ||
				got.TotalPledged != tt.want.TotalPledged || got.IsFundingClosed != tt.want.IsFundingClosed {
				t.Errorf("NewTestOccasion(%v) = %+v, want %+v", tt.opts, got, tt.want)
			}
		})
	}
}
```
