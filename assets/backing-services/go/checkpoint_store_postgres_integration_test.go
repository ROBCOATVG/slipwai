//go:build integration

// The checkpoint store against real Postgres, plus the one thing only a real store can prove.
//
// Behind the `integration` build tag, like its sibling, so `make verify` never compiles it:
//
//	make services-up migrate test-integration
//
// The contract runs here as it does against the fakes. The test below it is the one that cannot run
// anywhere else — two connections claiming one lease at the same instant, where exactly one must
// win. That is the whole basis for running a projection on more than one replica.
package checkpointstorepostgres_test

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"example.com/delivery-starter/adapters/driven/checkpointstorepostgres"
	"example.com/delivery-starter/adapters/driven/eventstorepostgres"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
	"example.com/delivery-starter/checkpointstorecontract"
)

// openPool turns a refused connection or a missing table into the instruction that fixes it.
func openPool(t *testing.T) *pgxpool.Pool {
	t.Helper()

	url := os.Getenv("DATABASE_URL")
	if strings.TrimSpace(url) == "" {
		t.Fatal("DATABASE_URL is unset, so there is no database to test against. Run " +
			"`make test-integration`, which sets it, after `make services-up migrate`.")
	}
	pool, err := pgxpool.New(context.Background(), url)
	if err != nil {
		t.Fatalf("cannot reach the database at %s: %v\nStart it first:  make services-up migrate",
			url, err)
	}
	statement := "SELECT 1 FROM projection_checkpoints LIMIT 1"
	if _, err := pool.Exec(context.Background(), statement); err != nil {
		pool.Close()
		t.Fatalf("cannot read the projection_checkpoints table: %v\nApply the schema first:  "+
			"make services-up migrate", err)
	}
	t.Cleanup(pool.Close)
	return pool
}

func TestPostgresCheckpointStoreSatisfiesThePort(t *testing.T) {
	pool := openPool(t)
	checkpointstorecontract.Run(t, func(*testing.T) (events.Store, readmodels.Store) {
		store := eventstorepostgres.New(pool)
		return store, checkpointstorepostgres.New(store)
	})
}

// The assertion no infrastructure-free adapter can make.
//
// The claim is one statement — an upsert whose WHERE decides whether the lease is takeable — so
// there is no window between reading who holds it and writing that you do. The in-memory adapter
// serialises every call behind a mutex and would pass this while proving nothing; SQLite
// serialises writers, so it would too.
func TestExactlyOneOfManySimultaneousClaimsWins(t *testing.T) {
	pool := openPool(t)
	projection := "race-" + randomID(t)
	now := time.Now().UTC()

	const attempts = 8
	taken := make([]bool, attempts)
	var group sync.WaitGroup
	var start sync.WaitGroup
	start.Add(1)
	for i := 0; i < attempts; i++ {
		group.Add(1)
		go func(index int) {
			defer group.Done()
			// Its own store per worker, so the claims contend on the database rather than queue
			// behind one connection.
			checkpoints := checkpointstorepostgres.New(eventstorepostgres.New(pool))
			start.Wait()
			// A name per worker, not one shared name: the holder of a lease may always renew
			// it, so eight claims under one name are eight renewals and prove nothing.
			owner := fmt.Sprintf("worker-%d", index)
			_, ok, err := checkpoints.Claim(
				context.Background(), projection, owner, now, 30*time.Second,
			)
			if err != nil {
				t.Errorf("claim %d: %v", index, err)
				return
			}
			taken[index] = ok
		}(i)
	}
	start.Done()
	group.Wait()

	winners := 0
	for _, ok := range taken {
		if ok {
			winners++
		}
	}
	if winners != 1 {
		t.Fatalf("expected exactly one worker to take the lease, got %d", winners)
	}
}

// A lease that only one process can see is not a lease. It is committed on its own, unlike a
// position, because coordination has to be visible before the work it coordinates.
func TestALeaseIsVisibleToAnotherConnectionAtOnce(t *testing.T) {
	pool := openPool(t)
	other, err := pgxpool.New(context.Background(), os.Getenv("DATABASE_URL"))
	if err != nil {
		t.Fatalf("second pool: %v", err)
	}
	t.Cleanup(other.Close)

	projection := "visible-" + randomID(t)
	first := checkpointstorepostgres.New(eventstorepostgres.New(pool))
	second := checkpointstorepostgres.New(eventstorepostgres.New(other))

	if _, ok, err := first.Claim(context.Background(), projection, "worker-1",
		checkpointstorecontract.Now, 30*time.Second); err != nil || !ok {
		t.Fatalf("expected the first claim to be granted, got ok=%v (%v)", ok, err)
	}
	if _, ok, err := second.Claim(context.Background(), projection, "worker-2",
		checkpointstorecontract.Now, 30*time.Second); err != nil || ok {
		t.Fatalf("expected the second connection to be refused, got ok=%v (%v)", ok, err)
	}
}

func randomID(t *testing.T) string {
	t.Helper()
	buffer := make([]byte, 8)
	if _, err := rand.Read(buffer); err != nil {
		t.Fatalf("random id: %v", err)
	}
	return hex.EncodeToString(buffer)
}
