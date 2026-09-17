```java
import com.example.shop.users.User;   // the real type

/**
 * Every field the type requires, so a test can name only the one it cares about. A fixed clock rather
 * than Instant.now(): a factory that reads the wall clock makes its own output different on every run.
 */
static UserBuilder aUser() {
    return new UserBuilder()
            .id(new UserId("user-123"))
            .name("Test User")
            .email(new Email("test@example.com"))
            .role(Role.USER)
            .active(true)
            .registeredAt(Instant.parse("2024-01-01T00:00:00Z"));
}
```
