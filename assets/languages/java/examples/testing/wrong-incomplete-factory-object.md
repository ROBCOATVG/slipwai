```java
// Will not even compile against a record with more components — and where it does compile, against a
// class with a no-argument constructor, it hands the code under test a User production never sees.
static User aUser() {
    return new User(new UserId("user-123"));  // no name, no email, no role
}
```
