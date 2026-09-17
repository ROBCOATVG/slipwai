package com.example.deliverystarter.adapters.driven.eventstorepostgres;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.Condition;
import com.example.deliverystarter.application.ports.events.ConditionalAppendResult;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.TagQuery;
import com.example.deliverystarter.application.ports.events.TagsOf;
import com.example.deliverystarter.adapters.driven.sql.Transactions;
import com.example.deliverystarter.eventstorecontract.EventStoreContract;
import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.HexFormat;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.ArrayList;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The event store against real Postgres.
 *
 * <p>Named {@code *IT}, so Surefire never sees it and {@code make verify} never compiles a database into the
 * gate. {@code make test-integration} runs Failsafe, which does:
 *
 * <pre>
 * make services-up migrate test-integration
 * </pre>
 *
 * <p>It runs the same contract the infrastructure-free adapters pass, plus the four things only a real
 * store can prove: that two appends at one version produce exactly one winner, that two conditional appends
 * against one <em>boundary</em> do the same, that the log refuses to be rewritten, and that a replay never
 * runs past a position an earlier event could still commit behind.
 *
 * <p>{@code @QuarkusTest} because the datasource under test is the application's own — Agroal, configured
 * from {@code DATABASE_URL} through {@code config/DatabaseUrlConfigSource}. Constructing a connection pool
 * here instead would test a pool this service never uses.
 */
@QuarkusTest
class PostgresEventStoreIT extends EventStoreContract {

    private static final SecureRandom RANDOM = new SecureRandom();

    @Inject
    DataSource dataSource;

    /**
     * The application's own transactions — the bean a slice would get — so what races below is the store
     * as it ships rather than a transaction strategy invented in a test.
     */
    @Inject
    Transactions transactions;

    @BeforeEach
    void requireTheSchema() {
        // Turns a refused connection or a missing table into the instruction that fixes it. Without this the
        // first failure is a driver error, and the reader has to already know the schema is applied by a
        // separate target.
        try (Connection connection = dataSource.getConnection();
                Statement statement = connection.createStatement()) {
            statement.executeQuery("SELECT 1 FROM events LIMIT 1").close();
        } catch (SQLException failure) {
            throw new IllegalStateException(
                    "cannot read the events table: " + failure.getMessage()
                            + "\nStart the database and apply the schema first:  make services-up migrate",
                    failure);
        }
    }

    @Override
    protected EventStore newStore(TagsOf tagsOf) {
        return new PostgresEventStore(transactions, tagsOf);
    }

    /**
     * Tag an event by the seat it is claiming, which is what the boundary below is drawn out of. A real
     * project's tagging function is this shape: the identifying attributes, derived.
     */
    private static final TagsOf SEAT_TAGS = candidate ->
            candidate.payload().get("seatId") instanceof String seat
                    ? List.of("seat:" + seat)
                    : List.of();


    /**
     * The assertion no infrastructure-free store can make.
     *
     * <p>The in-memory adapter serialises every call behind one lock and can never produce two winners, so it
     * would pass this test while proving nothing. SQLite serialises writers for the same reason. Only a real
     * store genuinely races, which is why this guarantee is proved here and nowhere else.
     */
    @Test
    void exactlyOneOfManySimultaneousFirstWritesWins() throws Exception {
        EventStore store = newStore();
        String stream = randomStream("race");
        int attempts = 8;

        CountDownLatch gate = new CountDownLatch(1);
        List<Future<AppendResult>> attempted = new ArrayList<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(attempts)) {
            for (int index = 0; index < attempts; index++) {
                DomainEvent attempt = event(stream, "Attempt" + index);
                attempted.add(pool.submit(() -> {
                    // Every task waits on the same gate, so they contend rather than queue.
                    gate.await();
                    return store.append(stream, EventStore.NO_STREAM, List.of(attempt));
                }));
            }
            gate.countDown();
        }

        int winners = 0;
        for (Future<AppendResult> pending : attempted) {
            AppendResult result = pending.get();
            if (result instanceof AppendResult.Appended) {
                winners++;
            } else if (result instanceof AppendResult.VersionConflict conflict) {
                assertThat(conflict.actualVersion()).isZero();
            }
        }

        assertThat(winners).as("exactly one append may win").isEqualTo(1);
        assertThat(store.read(stream)).hasSize(1);
    }

    /**
     * The Dynamic Consistency Boundary, raced for real — and the case {@code expectedVersion} cannot
     * express, because each attempt writes to a <em>different</em> stream and the thing they contend for is
     * a tag they share.
     *
     * <p>The boundary is read <strong>once</strong>, and all eight attempts are guarded by that one
     * position: eight callers who each decided, from the same facts, that the seat was free. Exactly one may
     * record it. Some lose because the winner's event is already there when they check; the rest lose to
     * SERIALIZABLE at commit, which is reported as the same conflict and needs the same next move from the
     * caller. No single-writer store can produce this situation at all, which is why the guarantee is
     * proved here and nowhere else.
     *
     * <p>Reading the head inside each attempt would test something else entirely — whichever attempt
     * happened to read after the winner committed would be guarded from a position past the winner's event,
     * and would rightly be allowed to write. A caller that re-reads has re-decided, and this test is about
     * callers that have not.
     */
    @Test
    void exactlyOneOfManySimultaneousConditionalAppendsWins() throws Exception {
        EventStore store = newStore(SEAT_TAGS);
        String seat = randomStream("seat");
        TagQuery query = TagQuery.tagged("seat:" + seat);
        long decidedAt = store.readTagged(query, 0).head();
        int attempts = 8;

        CountDownLatch gate = new CountDownLatch(1);
        List<Future<ConditionalAppendResult>> attempted = new ArrayList<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(attempts)) {
            for (int index = 0; index < attempts; index++) {
                DomainEvent claim = event(
                        "claim-" + seat + "-" + index, "SeatClaimed", Map.of("seatId", seat));
                attempted.add(pool.submit(() -> {
                    // Every task waits on the same gate, so they contend rather than queue.
                    gate.await();
                    return store.appendIf(new Condition(query, decidedAt), List.of(claim));
                }));
            }
            gate.countDown();
        }

        int winners = 0;
        for (Future<ConditionalAppendResult> pending : attempted) {
            if (pending.get() instanceof ConditionalAppendResult.Recorded) {
                winners++;
            }
        }

        assertThat(winners).as("exactly one conditional append may win").isEqualTo(1);
        assertThat(store.readTagged(query, 0).events()).hasSize(1);
    }

    /**
     * The guarantee a projection's single-number checkpoint rests on, and the one bug in this design that
     * leaves no trace.
     *
     * <p>A position is assigned when a row is inserted and becomes visible when its transaction commits,
     * and those are two different moments: two appends overlapping take 5 and 6, and 6 can commit first. A
     * replay that hands out 6 while 5 is still in flight makes the projection record "next is 7", and 5
     * then arrives behind a checkpoint that has already passed it — a view missing a row, permanently, with
     * a log that is perfectly correct and nothing anywhere complaining.
     *
     * <p>So {@code readAll} waits for the appends in flight and stops at the last settled position. The
     * replay below finishes only <em>after</em> the slow append commits, and then it holds both events in
     * order. Without the protocol it would finish at once, holding the second event and not the first.
     *
     * <p>Only a real store can produce this at all: the in-memory adapter is one lock and SQLite serialises
     * its writers, so in neither can a position be taken and committed out of order.
     *
     * <p>Three stores over the framework's transactions rather than one, and three threads: a transaction
     * belongs to the thread that opened it, so this is what "two appends overlapping" has to be built out
     * of here.
     */
    @Test
    void stopsAReplayShortOfAPositionAnEarlierEventCouldStillArriveBehind() throws Exception {
        EventStore slow = newStore();
        EventStore fast = newStore();
        EventStore reader = newStore();
        String first = randomStream("slow");
        String second = randomStream("fast");
        // Where this case's own events begin: the log is shared with every other case and every previous
        // run, so a replay from zero would read all of them.
        long start = reader.readTagged(new TagQuery(List.of()), 0).head() + 1;

        List<String> replayed = Collections.synchronizedList(new ArrayList<>());
        CountDownLatch replaying = new CountDownLatch(1);
        CountDownLatch finished = new CountDownLatch(1);
        CountDownLatch committed = new CountDownLatch(1);

        try (ExecutorService pool = Executors.newFixedThreadPool(3)) {
            Future<?> holding = pool.submit(() -> slow.inUnitOfWork(() -> {
                slow.append(first, EventStore.NO_STREAM, List.of(event(first, "Slow")));
                // Its position is taken; its commit is not. This one takes the next and commits.
                fast.append(second, EventStore.NO_STREAM, List.of(event(second, "Fast")));
                replaying.countDown();
                // Held open until the replay has had its chance to finish early, which is the failure
                // this case is about.
                await(committed);
                return Boolean.TRUE;
            }));
            pool.submit(() -> {
                await(replaying);
                reader.readAll(start, replayedEvent -> {
                    replayed.add(replayedEvent.type());
                    return true;
                });
                finished.countDown();
            });

            await(replaying);
            assertThat(finished.await(1, TimeUnit.SECONDS))
                    .as("a replay finished while an append was in flight, and read %s", replayed)
                    .isFalse();
            committed.countDown();
            holding.get(10, TimeUnit.SECONDS);

            assertThat(finished.await(10, TimeUnit.SECONDS))
                    .as("a replay never finished after the append committed")
                    .isTrue();
        }

        assertThat(replayed).containsExactly("Slow", "Fast");
    }

    /** A latch, waited on without making every caller declare the interruption. */
    private static void await(CountDownLatch latch) {
        try {
            if (!latch.await(30, TimeUnit.SECONDS)) {
                throw new IllegalStateException("waited 30s for a latch that never fell");
            }
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while waiting for a latch", interrupted);
        }
    }

    /**
     * The same gap as the replay's, on the write path, where it breaks the constraint instead of a view —
     * and this is the case the whole tag boundary rests on.
     *
     * <p>Two appends take 5 and 6; 6 commits first. A decision reading a head of 6 while 5 is still
     * invisible would be guarded from <em>after</em> 6 — and 5, the very event that should refuse it, sits
     * below its own boundary where the guard never looks. The append is allowed, the seat is claimed
     * twice, and the log looks perfectly correct afterwards.
     *
     * <p>So a boundary is only ever a settled position: {@code head} waits for the appends in flight,
     * which makes the read that follows see the event as well. The claim below is therefore refused, and
     * it is refused by the <em>condition</em> rather than by chance.
     */
    @Test
    void refusesAConditionalAppendAgainstAnEventInFlightWhenTheBoundaryWasRead() throws Exception {
        EventStore slow = newStore(SEAT_TAGS);
        EventStore fast = newStore(SEAT_TAGS);
        EventStore decider = newStore(SEAT_TAGS);
        String seat = randomStream("seat");
        TagQuery query = TagQuery.tagged("seat:" + seat);

        List<String> drawn = Collections.synchronizedList(new ArrayList<>());
        CountDownLatch appended = new CountDownLatch(1);
        CountDownLatch decided = new CountDownLatch(1);
        CountDownLatch committed = new CountDownLatch(1);

        try (ExecutorService pool = Executors.newFixedThreadPool(3)) {
            Future<?> holding = pool.submit(() -> slow.inUnitOfWork(() -> {
                String claim = "claim-" + seat + "-1";
                slow.append(claim, EventStore.NO_STREAM,
                        List.of(event(claim, "SeatClaimed", Map.of("seatId", seat))));
                // Its position is taken; its commit is not. This one takes the next and commits.
                String other = randomStream("other");
                fast.append(other, EventStore.NO_STREAM, List.of(event(other, "Unrelated")));
                appended.countDown();
                await(committed);
                return Boolean.TRUE;
            }));
            pool.submit(() -> {
                await(appended);
                // A decision, drawn the way every caller draws one: pin the boundary, then read it.
                long boundary = decider.head();
                decider.readTagged(query, 0, boundary).events()
                        .forEach(found -> drawn.add(found.type()));
                decided.countDown();
            });

            await(appended);
            assertThat(decided.await(1, TimeUnit.SECONDS))
                    .as("a boundary was drawn while an append was in flight, and read %s", drawn)
                    .isFalse();
            committed.countDown();
            holding.get(10, TimeUnit.SECONDS);

            assertThat(decided.await(10, TimeUnit.SECONDS))
                    .as("a boundary was never drawn after the append committed")
                    .isTrue();
        }

        // The decision now knows about the claim, which is the whole point of waiting.
        assertThat(drawn).containsExactly("SeatClaimed");

        // And a caller that decided anyway is refused by the condition rather than by luck.
        ConditionalAppendResult refused = decider.appendIf(new Condition(query, 0),
                List.of(event("claim-" + seat + "-2", "SeatClaimed", Map.of("seatId", seat))));
        assertThat(refused).isInstanceOf(ConditionalAppendResult.ConditionConflict.class);
    }

    @Test
    void refusesToLetACommittedEventBeRewrittenOrRemoved() throws SQLException {
        EventStore store = newStore();
        String stream = randomStream("append-only");
        store.append(stream, EventStore.NO_STREAM, List.of(event(stream, "Recorded")));

        try (Connection connection = dataSource.getConnection();
                Statement statement = connection.createStatement()) {
            for (String forbidden : List.of(
                    "UPDATE events SET event_type = 'Rewritten' WHERE stream_id = '" + stream + "'",
                    "DELETE FROM events WHERE stream_id = '" + stream + "'")) {
                assertThatThrownBy(() -> statement.executeUpdate(forbidden))
                        .as(forbidden)
                        .isInstanceOf(SQLException.class)
                        .hasMessageContaining("append-only");
            }
        }

        List<CommittedEvent> recorded = store.read(stream);
        assertThat(recorded).hasSize(1);
        assertThat(recorded.get(0).type()).isEqualTo("Recorded");
    }

    /**
     * A fresh stream per run. The log is append-only, so a database shared with a previous run cannot be
     * cleaned — a fresh name is the only way to assert about only this run's events.
     */
    private static String randomStream(String prefix) {
        byte[] buffer = new byte[8];
        RANDOM.nextBytes(buffer);
        return prefix + "-" + HexFormat.of().formatHex(buffer);
    }
}
