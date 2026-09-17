```java
// The real Email lives in com.example.shop.users, and validates. This is a second one that does not,
// so every test using it passes on values the application would have refused.
record Email(String value) { }

static UserBuilder aUser() {
    return new UserBuilder().email(new Email("not-an-email"));
}
```
