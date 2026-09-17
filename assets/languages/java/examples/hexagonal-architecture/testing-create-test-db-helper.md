```java
/**
 * A fresh database per test, so no case depends on what another left behind.
 *
 * <p>`:memory:` here; a container for real Postgres in the integration suite. The important part is that
 * the helper migrates: a test database whose schema was applied by hand drifts from the one production
 * gets, and the tests keep passing while it does.
 */
static DataSource testDatabase() {
    SQLiteDataSource dataSource = new SQLiteDataSource();
    dataSource.setUrl("jdbc:sqlite::memory:");
    Flyway.configure().dataSource(dataSource).load().migrate();
    return dataSource;
}
```
