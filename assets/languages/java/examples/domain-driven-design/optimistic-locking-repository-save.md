```java
/**
 * The expected version in the WHERE clause *is* the lock. No rows updated means somebody else wrote first,
 * which is a value the caller can act on rather than an exception.
 *
 * <p>A SELECT-then-UPDATE would have a window between the two; this has none, because the check and the
 * write are one statement.
 */
@Override
public Saved save(Occasion occasion, int expectedVersion) {
    try (Connection connection = dataSource.getConnection();
            PreparedStatement statement = connection.prepareStatement("""
                    UPDATE occasions
                       SET name = ?, budget_minor_units = ?, pledged_minor_units = ?, version = ?
                     WHERE id = ? AND version = ?
                    """)) {
        statement.setString(1, occasion.name());
        statement.setLong(2, occasion.budget().minorUnits());
        statement.setLong(3, occasion.totalPledged().minorUnits());
        statement.setInt(4, expectedVersion + 1);
        statement.setString(5, occasion.id().value());
        statement.setInt(6, expectedVersion);
        return statement.executeUpdate() == 1 ? Saved.SAVED : Saved.CONFLICT;
    } catch (SQLException failure) {
        throw new OccasionRepositoryException("save occasion " + occasion.id(), failure);
    }
}
```
