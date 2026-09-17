```java
// Technology leaks through the port, so every implementation must be a SQL database with a Redis beside it.
interface UserRepository {
    List<User> findBySqlQuery(String sql);

    User getFromRedisCache(String key);
}

// Business language, so the port says what the application needs and nothing about how.
interface UserRepository {
    List<User> findActive();

    Optional<User> findById(UserId id);
}
```
