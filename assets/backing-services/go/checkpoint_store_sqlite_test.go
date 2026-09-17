package checkpointstoresqlite_test

import (
	"testing"

	"example.com/delivery-starter/adapters/driven/checkpointstoresqlite"
	"example.com/delivery-starter/adapters/driven/eventstoresqlite"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
	"example.com/delivery-starter/checkpointstorecontract"
)

// The checkpoint contract, against SQLite — one file, one connection, real transactions.
//
// This is the cheapest place the transactional checkpoint is genuinely proved: the in-memory
// adapter rolls back by restoring a copy, whereas here a failed unit of work is a real ROLLBACK
// issued by a real database. ":memory:" because the contract is about behaviour and a fresh
// database per case is what keeps them independent.
func TestSqliteCheckpointStoreSatisfiesThePort(t *testing.T) {
	checkpointstorecontract.Run(t, func(t *testing.T) (events.Store, readmodels.Store) {
		store, err := eventstoresqlite.Open(":memory:")
		if err != nil {
			t.Fatalf("open sqlite: %v", err)
		}
		t.Cleanup(func() { store.Close() })
		return store, checkpointstoresqlite.New(store)
	})
}
