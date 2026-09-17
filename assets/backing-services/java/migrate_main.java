package com.example.deliverystarter.migrations;

import com.example.deliverystarter.config.DatabaseUrl;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.FlywayException;
import org.flywaydb.core.api.output.MigrateResult;

/**
 * Applies the event-store migrations, in order, exactly once each.
 *
 * <pre>
 * make migrate
 * cd apps/service &amp;&amp; DATABASE_URL=postgres://app:app@localhost:5433/app ./mvnw -DskipTests compile exec:java
 * </pre>
 *
 * <p>This class does not implement a migration runner, and that distinction matters. Flyway does all of it:
 * the ordering by the {@code V<n>__} prefix, the {@code flyway_schema_history} ledger, the one-transaction
 * -per-migration guarantee, and the refusal to re-run or re-order what has already been applied. What is
 * here is the twelve lines that hand Flyway a database — because the framework's Flyway integration is
 * configured to migrate on command rather than at start-up, and a command needs an entry point that exits.
 *
 * <p>Why not at start-up: writing to a database is an explicit act, and a service that migrates as it boots
 * migrates once per replica during a rolling deploy. `quarkus.flyway.migrate-at-start` is set to false in
 * `application.properties` for exactly that reason.
 *
 * <p>There are no down migrations. Reversing an event-log schema change is a reviewed operation, and a
 * rollback that lives next to its migration is a rollback that eventually runs by accident.
 *
 * <p>Why the failure path below flattens its own exception: {@code make migrate} runs Maven with {@code -q},
 * and under {@code -q} Maven renders a failed mojo's exception after the project's class loader is gone. A
 * Flyway exception whose message formatting reaches for one more Flyway class then reports as
 * {@code A required class was missing … org/flywaydb/core/internal/util/ExceptionUtils} instead of
 * "connection refused" — which is the most likely way this command ever fails, and the least helpful thing
 * it could say about it. Reading the chain here, while the loader is alive, and rethrowing a plain message
 * keeps the diagnosis this program's rather than Maven's.
 */
public final class MigrateMain {

    /** Enough to reach the driver's own message from Flyway's, with room to spare. */
    private static final int MAX_CAUSE_DEPTH = 8;

    private MigrateMain() {
    }

    // A command-line entry point reports on stdout: that is its interface, not a stray debug print, so
    // the ban on System.out is lifted here and nowhere else in the project.
    // SystemPrintln: a command-line entry point reports on stdout — that is its interface, not a stray
    // debug print. PreserveStackTrace: dropping the cause is the entire point of the rethrow below, since a
    // cause is one more object Maven would format after the class loader that can format it is gone.
    @SuppressWarnings({"PMD.SystemPrintln", "PMD.PreserveStackTrace"})
    public static void main(String[] args) {
        DatabaseUrl database = DatabaseUrl.parse(System.getenv("DATABASE_URL"));
        MigrateResult result;
        try {
            result = Flyway.configure()
                    .dataSource(database.jdbcUrl(), database.username(), database.password())
                    .locations("classpath:db/migration")
                    // Off, because this project's first migration creates the events table in a database
                    // that may already hold other things. Baselining on migrate would silently mark
                    // existing migrations as applied, which is the one way to lose a migration without an
                    // error.
                    .baselineOnMigrate(false)
                    .load()
                    .migrate();
        } catch (FlywayException failure) {
            // Read here rather than left for Maven to render — see the note on this class. The rethrown
            // exception carries no cause on purpose: a cause is another object Maven would format later,
            // which is the whole problem.
            throw new IllegalStateException("migrate failed: " + describe(failure));
        }

        if (result.migrationsExecuted == 0) {
            System.out.println("migrate: up to date");
            return;
        }
        result.migrations.forEach(migration ->
                System.out.println("migrate: applied " + migration.filepath));
        System.out.println("migrate: applied " + result.migrationsExecuted + " migration(s)");
    }

    /**
     * The whole cause chain as one string, because the innermost cause is the useful one.
     *
     * <p>"Connection refused" is three levels below the Flyway exception a caller would otherwise see, and
     * the level in between adds nothing. The depth cap is what guarantees this terminates: it costs one
     * constant, and it means no chain shape can make a diagnostic hang.
     */
    private static String describe(Throwable failure) {
        StringBuilder described = new StringBuilder(failure.getClass().getSimpleName())
                .append(": ")
                .append(failure.getMessage());
        Throwable cause = failure.getCause();
        for (int depth = 0; cause != null && depth < MAX_CAUSE_DEPTH; depth++) {
            described.append(System.lineSeparator())
                    .append("  caused by ")
                    .append(cause.getClass().getSimpleName())
                    .append(": ")
                    .append(cause.getMessage());
            cause = cause.getCause();
        }
        return described.toString();
    }
}
