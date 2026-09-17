```java
// BEFORE — transport, validation, persistence and four business rules in one method. Nothing here can
// be tested without HTTP and a database, and nothing here can be reached by a second entry point.
@Path("/balance")
public class BalanceResource {

    @Inject
    DataSource dataSource;

    @POST
    @Path("/deduct")
    @Transactional
    public Response deduct(@Context SecurityContext security, DeductBody body) throws SQLException {
        if (security.getUserPrincipal() == null) {
            return Response.status(401).entity(Map.of("error", "unauthorized")).build();
        }
        try (Connection connection = dataSource.getConnection()) {
            UserRow user = load(connection, security.getUserPrincipal().getName());
            if (user == null) {
                return Response.status(404).entity(Map.of("error", "not-found")).build();
            }
            if (body.amountMinorUnits() <= 0) {
                return Response.status(422).entity(Map.of("error", "invalid-amount")).build();
            }
            if (!body.currency().equals(user.currency())) {
                return Response.status(422).entity(Map.of("error", "currency-mismatch")).build();
            }
            if (user.balanceMinorUnits() < body.amountMinorUnits()) {
                return Response.status(422).entity(Map.of("error", "insufficient-balance")).build();
            }
            long balance = user.balanceMinorUnits() - body.amountMinorUnits();
            update(connection, user.id(), balance);
            return Response.ok(Map.of("balanceMinorUnits", balance)).build();
        }
    }
}
```
