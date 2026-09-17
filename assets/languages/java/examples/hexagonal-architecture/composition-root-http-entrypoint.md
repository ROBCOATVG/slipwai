```java
/**
 * The composition root on this backend is the framework's: CDI builds the graph, so a producer method
 * declares what implements a port and Quarkus injects it. That is the same idea as a hand-written `main`
 * wiring adapters together — the difference is only who calls the constructor.
 */
@ApplicationScoped
class OrderWiring {

    @Produces
    @ApplicationScoped
    OrderRepository orderRepository(DataSource dataSource) {
        return new JdbcOrderRepository(dataSource);
    }

    @Produces
    @ApplicationScoped
    PaymentGateway paymentGateway(@ConfigProperty(name = "stripe.key") String key) {
        return new StripePaymentGateway(key);
    }

    @Produces
    @ApplicationScoped
    ForPlacingOrders orderPlacement(OrderRepository orders, PaymentGateway payments) {
        return new OrderPlacement(orders, payments);
    }
}

/** The driving adapter. Parse, call the use case, map the outcome to a status. No rules here. */
@Path("/orders")
public class OrderResource {

    private final ForPlacingOrders orders;

    OrderResource(ForPlacingOrders orders) {
        this.orders = orders;
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    public Response place(@Valid PlaceOrderBody body) {
        OrderResult result = orders.placeOrder(body.toCommand());
        return switch (result) {
            case OrderResult.Placed placed -> Response.ok(OrderView.of(placed.order())).build();
            case OrderResult.Refused refused -> Response.status(statusFor(refused.reason()))
                    .entity(Map.of("error", refused.reason()))
                    .build();
        };
    }
}
```
