```java
// A fake: real behaviour, real state, implementing the real interface. It can disagree with the code under
// test, which is what makes a passing test mean something.
public final class InMemoryUserRepository implements UserRepository {

    private final Map<UserId, User> users = new HashMap<>();

    public InMemoryUserRepository(User... initial) {
        for (User user : initial) {
            users.put(user.id(), user);
        }
    }

    @Override
    public Optional<User> findById(UserId id) {
        return Optional.ofNullable(users.get(id));
    }

    @Override
    public void save(User user) {
        users.put(user.id(), user);
    }
}

// A mock: verifies calls rather than behaviour. It returns whatever it was told to, so it agrees with the
// test by construction — and keeps agreeing after the repository's real contract changes.
UserRepository users = mock(UserRepository.class);
when(users.findById(any())).thenReturn(Optional.of(aUser().build()));
```
