```java
// The domain reaches for JDBC, so it cannot be tested, reused, or reasoned about without a database.
import javax.sql.DataSource;

public final class Users {
    public List<User> findActive(DataSource dataSource) throws SQLException { }
}

// The application declares the contract it consumes; an adapter in the outer ring implements it.
public interface UserRepository {
    List<User> findActive();
}
```
