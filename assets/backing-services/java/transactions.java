package com.example.deliverystarter.adapters.driven.sql;

import com.example.deliverystarter.application.ports.events.EventStoreException;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.function.Supplier;

/**
 * The framework's transaction manager, as a SQL adapter needs it.
 *
 * <p>Two questions, and both are the framework's to answer rather than this repository's:
 *
 * <ol>
 *   <li><strong>Which connection am I on?</strong> Inside a transaction, every participant has to use the
 *       same one — an adapter that takes a second connection from the pool has started a second
 *       transaction, and then "the view was written with the events" is a sentence rather than a
 *       guarantee. Spring answers with {@code DataSourceUtils.getConnection}, Quarkus with JTA and
 *       Agroal: ask either for a connection inside a transaction and you get that transaction's.
 *   <li><strong>Who commits?</strong> The outermost block, and only when it returns.
 * </ol>
 *
 * <p>Why a port and not a {@link javax.sql.DataSource} used directly: a store that manages its own
 * connections cannot be enlisted in anybody else's transaction, and that is the whole of the read side. A
 * view maintained {@code inline} is written in the append's transaction; a checkpoint is recorded in the
 * transaction that wrote the rows it accounts for. Delegating to the framework means the project's own
 * repository — {@code JdbcTemplate}, JPA, Panache, whatever it uses — joins that transaction by doing
 * nothing at all, because the framework was already the thing binding a connection to it. Hand-rolled
 * pinning could only ever enlist adapters written against this one class.
 *
 * <p>The implementation is one bean per framework, in {@code adapters/driven/sql/}, and it is the only
 * class in the project that names a transaction API.
 */
public interface Transactions {

    /**
     * Run {@code work} in one transaction, joining the caller's if there is one.
     *
     * <p>Joining takes a savepoint, because an inner block that fails has to undo its own writes and no
     * more. In Postgres it <em>has</em> to and not merely ought to: a failed statement poisons the whole
     * transaction until something rolls back to a savepoint, so without one an inner failure would take
     * the outer commit with it. That is how a refused append inside somebody else's unit of work leaves
     * both the transaction and the caller's other writes intact.
     */
    <T> T inTransaction(Isolation isolation, Supplier<T> work);

    /**
     * Whether a transaction is open on this thread.
     *
     * <p>Asked by a store deciding whether it may wait for the log to settle. Waiting takes the log's
     * lock exclusively, and a transaction that has already appended is holding that lock in shared mode —
     * so it would be waiting on itself. Inside a transaction the honest answer to "what is the head" is
     * that transaction's own view: a caller reading its own writes rather than drawing a boundary.
     */
    boolean isActive();

    /**
     * Run {@code work} on this transaction's connection, or on one of the pool's outside a transaction.
     *
     * <p>Every read and write in a SQL adapter goes through here, which is what makes "inside a unit of
     * work, nothing commits on its own" true by construction rather than by discipline.
     */
    <T> T onConnection(String what, SqlWork<T> work);

    /**
     * What a transaction has to prove, which is not always the same thing.
     *
     * <p>{@code SERIALIZABLE} is what a conditional append needs: there is no version to compare, so what
     * it must prove is that <em>nothing matching a query</em> arrived since the caller read, and the
     * database is what proves it. The cost is real and it is the caller's — a serialisation failure is
     * reported as a conflict, and the caller re-reads and re-decides exactly as it does for a stale
     * version. Asked for as the transaction opens, which is the only place it can be answered, so a
     * conditional append called inside somebody else's unit of work runs at that transaction's level.
     */
    enum Isolation {
        DEFAULT,
        SERIALIZABLE
    }

    /**
     * Something to do with a connection, which may fail the way JDBC fails.
     *
     * <p>One shape rather than a void overload beside it, which javac cannot tell apart from this one at a
     * block-bodied call site. Work that produces nothing ends {@code return Boolean.TRUE} — deliberately
     * not {@code null}, which this project's null analysis refuses on sight and is right to.
     */
    @FunctionalInterface
    interface SqlWork<T> {

        T run(Connection connection) throws SQLException;
    }

    /** A JDBC failure as this project reports it, so every implementation says it the same way. */
    static EventStoreException failed(String what, SQLException failure) {
        return new EventStoreException(what, failure);
    }
}
