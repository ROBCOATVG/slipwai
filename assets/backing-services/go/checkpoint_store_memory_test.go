package checkpointstorememory_test

import (
	"testing"

	"example.com/delivery-starter/adapters/driven/checkpointstorememory"
	"example.com/delivery-starter/adapters/driven/eventstorememory"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
	"example.com/delivery-starter/checkpointstorecontract"
)

// The checkpoint contract, against the fake. Runs in `make verify` with no Docker, which is the
// whole reason the in-memory adapters exist. What it cannot prove is two workers genuinely racing
// for one lease — this one serialises them — and `make test-integration` is where that is proved.
func TestInMemoryCheckpointStoreSatisfiesThePort(t *testing.T) {
	checkpointstorecontract.Run(t, func(*testing.T) (events.Store, readmodels.Store) {
		store := eventstorememory.New()
		return store, checkpointstorememory.New(store)
	})
}
