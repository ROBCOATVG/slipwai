```go
package ddd

type Occasion struct {
	ID        OccasionID
	Version   int // incremented on each save
	Name      string
	Budget    Money
	GiftIdeas []GiftIdea
}
```
