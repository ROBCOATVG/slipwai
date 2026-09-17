package com.example.deliverystarter.adapters.driven.sql;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Objects;
import java.util.function.Supplier;
import javax.sql.DataSource;
import org.springframework.jdbc.datasource.DataSourceUtils;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Transactions, the way Spring does them.
 *
 * <p>Two framework mechanisms, and between them there is nothing left for this project to hand-roll:
 *
 * <ul>
 *   <li>{@link TransactionTemplate} is the programmatic half of {@code @Transactional} — the same
 *       {@link PlatformTransactionManager}, the same propagation rules, so a store used inside an
 *       annotated service method joins that method's transaction instead of opening one beside it.
 *   <li>{@link DataSourceUtils#getConnection} returns the connection Spring has bound to the current
 *       transaction, or a fresh one when there is none. That is the whole reason no {@link ThreadLocal}
 *       appears in this project: the framework was already binding a connection per transaction, and
 *       anything else that asks — {@code JdbcTemplate}, JPA, a repository of the project's own — gets the
 *       same one.
 * </ul>
 *
 * <p>{@code PROPAGATION_NESTED} is a savepoint, which is exactly the undo boundary a nested block needs,
 * and {@code DataSourceTransactionManager} allows it by default. With no transaction open it behaves like
 * {@code REQUIRED} and starts one.
 *
 * <p>A bean, unlike the stores themselves: there is exactly one transaction manager in an application, so
 * an injection point for it is unambiguous. Which event store the application uses is still a composition
 * decision the project takes for itself.
 */
@Component
public class SpringTransactions implements Transactions {

    private final DataSource dataSource;
    private final PlatformTransactionManager transactionManager;

    SpringTransactions(DataSource dataSource, PlatformTransactionManager transactionManager) {
        this.dataSource = dataSource;
        this.transactionManager = transactionManager;
    }

    @Override
    public <T> T inTransaction(Isolation isolation, Supplier<T> work) {
        TransactionTemplate template = new TransactionTemplate(transactionManager);
        template.setPropagationBehavior(TransactionDefinition.PROPAGATION_NESTED);
        if (isolation == Isolation.SERIALIZABLE) {
            // Applied when this template opens the transaction. Joining one, Spring leaves the level
            // alone — a participant does not get to change the isolation of a transaction already under
            // way, and Postgres would refuse it anyway.
            template.setIsolationLevel(TransactionDefinition.ISOLATION_SERIALIZABLE);
        }
        // `execute` is declared nullable because a Spring callback may return nothing. This port's
        // work never does: the {@code Runnable} overload on `EventStore` is what a unit of work with
        // nothing to hand back uses, precisely so no call site writes `return null`. So a null here is a
        // broken contract rather than an empty transaction, and it says so.
        return Objects.requireNonNull(
                template.execute(status -> work.get()), "a unit of work returned null");
    }

    @Override
    public boolean isActive() {
        return TransactionSynchronizationManager.isActualTransactionActive();
    }

    @Override
    public <T> T onConnection(String what, SqlWork<T> work) {
        Connection connection = DataSourceUtils.getConnection(dataSource);
        try {
            return work.run(connection);
        } catch (SQLException failure) {
            throw Transactions.failed(what, failure);
        } finally {
            // A no-op for a transaction-bound connection and a close for a standalone one, which is the
            // decision this call exists to take on our behalf.
            DataSourceUtils.releaseConnection(connection, dataSource);
        }
    }
}
