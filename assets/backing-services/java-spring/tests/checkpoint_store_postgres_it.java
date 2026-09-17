package com.example.deliverystarter.adapters.driven.checkpointstorepostgres;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.deliverystarter.adapters.driven.eventstorepostgres.PostgresEventStore;
import com.example.deliverystarter.adapters.driven.sql.Transactions;
import com.example.deliverystarter.checkpointstorecontract.CheckpointStoreContract;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * The checkpoint store against real Postgres, plus the one thing only a real store can prove.
 *
 * <p>Named {@code *IT}, like its sibling, so Surefire never sees it and {@code make verify} never
 * compiles a database into the gate:
 *
 * <pre>
 * make services-up migrate test-integration
 * </pre>
 *
 * <p>The contract runs here as it does against the fakes. The test below it is the one that cannot run
 * anywhere else — two connections claiming one lease at the same instant, where exactly one must win. That
 * is the whole basis for running a projection on more than one replica.
 */
@SpringBootTest
class PostgresCheckpointStoreIT extends CheckpointStoreContract {

    private static final SecureRandom RANDOM = new SecureRandom();

    @Autowired
    DataSource dataSource;

    /**
     * The application's own transactions, which is what makes this an integration test of the thing that
     * ships rather than of a transaction strategy invented in a test.
     */
    @Autowired
    Transactions transactions;

    @BeforeEach
    void requireTheSchema() {
        // Turns a refused connection or a missing table into the instruction that fixes it.
        try (Connection connection = dataSource.getConnection();
                Statement statement = connection.createStatement()) {
            statement.executeQuery("SELECT 1 FROM projection_checkpoints LIMIT 1").close();
        } catch (SQLException failure) {
            throw new IllegalStateException(
                    "cannot read the projection_checkpoints table: " + failure.getMessage()
                            + "\nStart the database and apply the schema first:  make services-up migrate",
                    failure);
        }
    }

    @Override
    protected Stores stores() {
        // Both adapters over the same transactions, which is the one thing this contract exists to
        // check: a checkpoint recorded beside the events it accounts for, in their transaction.
        return new Stores(
                new PostgresEventStore(transactions), new PostgresCheckpointStore(transactions));
    }

    /**
     * The assertion no infrastructure-free adapter can make.
     *
     * <p>The claim is one statement — an upsert whose {@code WHERE} decides whether the lease is takeable
     * — so there is no window between reading who holds it and writing that you do. The in-memory adapter
     * serialises every call behind one lock and would pass this while proving nothing; SQLite serialises
     * writers, so it would too.
     *
     * <p>A name per worker, not one shared name: the holder of a lease may always renew it, so eight claims
     * under one name are eight renewals and prove nothing.
     */
    @Test
    void exactlyOneOfManySimultaneousClaimsWins() throws Exception {
        String projection = "race-" + randomId();
        int attempts = 8;

        CountDownLatch gate = new CountDownLatch(1);
        List<Future<Optional<CheckpointStore.Lease>>> attempted = new ArrayList<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(attempts)) {
            for (int index = 0; index < attempts; index++) {
                String owner = "worker-" + index;
                // Its own store per worker, as two replicas would have. They contend on the database
                // rather than queue because a transaction belongs to the thread that opened it, which is
                // the framework's guarantee and not this adapter's.
                CheckpointStore checkpoints = new PostgresCheckpointStore(transactions);
                attempted.add(pool.submit(() -> {
                    // Every task waits on the same gate, so they contend rather than queue.
                    gate.await();
                    return checkpoints.claim(projection, owner, NOW, Duration.ofSeconds(30));
                }));
            }
            gate.countDown();
        }

        int winners = 0;
        for (Future<Optional<CheckpointStore.Lease>> pending : attempted) {
            if (pending.get().isPresent()) {
                winners++;
            }
        }

        assertThat(winners).as("exactly one worker may take the lease").isEqualTo(1);
    }

    /**
     * A lease that only one process can see is not a lease. It is committed on its own, unlike a position,
     * because coordination has to be visible before the work it coordinates.
     */
    @Test
    void makesALeaseVisibleToAnotherConnectionAtOnce() {
        String projection = "visible-" + randomId();
        CheckpointStore first = new PostgresCheckpointStore(transactions);
        CheckpointStore second = new PostgresCheckpointStore(transactions);

        assertThat(first.claim(projection, "worker-1", NOW, Duration.ofSeconds(30))).isPresent();
        assertThat(second.claim(projection, "worker-2", NOW, Duration.ofSeconds(30))).isEmpty();
    }

    private static String randomId() {
        byte[] buffer = new byte[8];
        RANDOM.nextBytes(buffer);
        return HexFormat.of().formatHex(buffer);
    }
}
