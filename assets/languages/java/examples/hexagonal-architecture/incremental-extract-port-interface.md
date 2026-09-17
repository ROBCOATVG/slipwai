```java
// application/UserRepository.java — an application-owned port. The version travels with the value,
// because the use case needs it to detect a concurrent change and the domain must not know it exists.
public interface UserRepository {

    Optional<StoredUser> findById(UserId id);

    Saved save(User user, int expectedVersion);

    record StoredUser(User value, int version) { }

    enum Saved { SAVED, CONFLICT }
}
```
