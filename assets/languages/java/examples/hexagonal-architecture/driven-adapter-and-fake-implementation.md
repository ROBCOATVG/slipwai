```java
/** A driven adapter over JDBC. */
final class JdbcUserRepository implements UserRepository {

    private final DataSource dataSource;

    JdbcUserRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Optional<User> findById(UserId id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT_BY_ID)) {
            statement.setString(1, id.value());
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? Optional.of(toUser(rows)) : Optional.empty();
            }
        } catch (SQLException failure) {
            throw new UserRepositoryException("find user " + id, failure);
        }
    }

    @Override
    public void save(User user) { }
}

/**
 * A second adapter for the same port, for tests. A real implementation with real behaviour, not a mock:
 * it stores what it is given and gives back what it stored, so a test that uses it fails when the use
 * case is wrong rather than when an expectation was written wrong.
 */
public final class InMemoryUserRepository implements UserRepository {

    private final Map<UserId, User> users = new HashMap<>();

    public InMemoryUserRepository(User... initial) {
        for (User user : initial) {
            users.put(user.id(), user);
        }
    }

    @Override
    public Optional<User> findById(UserId id) {
        return Optional.ofNullable(users.get(id));
    }

    @Override
    public void save(User user) {
        users.put(user.id(), user);
    }
}
```
