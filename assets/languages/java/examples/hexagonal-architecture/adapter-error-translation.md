```java
/** The port's vocabulary: one expected condition, named as the application understands it. */
public sealed interface CreateUserResult {
    record Created() implements CreateUserResult { }

    record AlreadyExists() implements CreateUserResult { }
}

/**
 * A driven adapter translating an expected storage condition into that vocabulary — and letting
 * everything else through untouched.
 */
final class JdbcUserRepository implements UserRepository {

    private static final String UNIQUE_VIOLATION = "23505";

    @Override
    public CreateUserResult create(User user) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(INSERT)) {
            bind(statement, user);
            statement.executeUpdate();
            return new CreateUserResult.Created();
        } catch (SQLException failure) {
            if (UNIQUE_VIOLATION.equals(failure.getSQLState())) {
                return new CreateUserResult.AlreadyExists();   // an expected outcome, so a value
            }
            // A lost connection or a full disk is not an outcome the application can decide about.
            // Wrapped, not swallowed: the caller sees a failure rather than a false "already exists".
            throw new UserRepositoryException("create user " + user.id(), failure);
        }
    }
}
```
