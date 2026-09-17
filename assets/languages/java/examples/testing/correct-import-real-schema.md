```java
import com.example.shop.users.User;   // the real type, not a copy of its shape

static UserBuilder aUser() {
    return new UserBuilder()
            .id(new UserId("user-123"))
            .name("Test User")
            .email(new Email("test@example.com"));
}

// User's canonical constructor validates, so a factory that builds an impossible User fails here
// rather than producing one the production code could never have received.
```
