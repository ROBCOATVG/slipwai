```java
// The resource talks to the database directly, so the rule about who may see what has no home.
@Path("/users")
public class UserResource {

    @Inject
    DataSource dataSource;

    @GET
    public List<UserView> active() throws SQLException {
        try (Connection connection = dataSource.getConnection()) { }
    }
}

// The resource calls a use case, which uses a port. The rule lives in one place and both entry points
// — this route and tomorrow's scheduled job — get it.
@Path("/users")
public class UserResource {

    private final ForListingActiveUsers users;

    @GET
    public List<UserView> active() {
        return users.listActive();
    }
}
```
