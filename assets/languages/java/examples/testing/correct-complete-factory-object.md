```java
/** A builder, because Java has no object spread — and it defaults every required field. */
static UserBuilder aUser() {
    return new UserBuilder()
            .id(new UserId("user-123"))
            .name("Test User")
            .email(new Email("test@example.com"))
            .role(Role.USER);
}

// build() calls the real constructor, so every invariant the type enforces runs here too.
User user = aUser().email(new Email("custom@example.com")).build();
```
