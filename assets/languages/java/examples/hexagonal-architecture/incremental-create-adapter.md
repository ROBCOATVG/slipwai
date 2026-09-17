```java
// adapters/driven/JdbcUserRepository.java — the port, over a real database.
final class JdbcUserRepository implements UserRepository {

    private final DataSource dataSource;

    JdbcUserRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Optional<StoredUser> findById(UserId id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "SELECT id, balance_minor_units, currency, version FROM users WHERE id = ?")) {
            statement.setString(1, id.value());
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next()
                        ? Optional.of(new StoredUser(toUser(rows), rows.getInt("version")))
                        : Optional.empty();
            }
        } catch (SQLException failure) {
            throw new UserRepositoryException("find user " + id, failure);
        }
    }

    /** The version in the WHERE clause is the optimistic lock: no rows updated means somebody else won. */
    @Override
    public Saved save(User user, int expectedVersion) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("""
                        UPDATE users SET balance_minor_units = ?, version = ?
                        WHERE id = ? AND version = ?
                        """)) {
            statement.setLong(1, user.balance().minorUnits());
            statement.setInt(2, expectedVersion + 1);
            statement.setString(3, user.id().value());
            statement.setInt(4, expectedVersion);
            return statement.executeUpdate() == 1 ? Saved.SAVED : Saved.CONFLICT;
        } catch (SQLException failure) {
            throw new UserRepositoryException("save user " + user.id(), failure);
        }
    }
}
```
