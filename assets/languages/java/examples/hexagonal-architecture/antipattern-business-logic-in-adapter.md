```java
// A business rule in the resource. The next entry point — a CLI, a queue consumer — will not have it.
@POST
public Response place(PlaceOrderBody body) {
    Order order = orders.findById(new OrderId(body.id())).orElseThrow();
    if (order.itemCount() > 100) {
        approvals.requireManagerApproval(order);   // a business rule, in the transport
    }
    return Response.ok().build();
}

// The rule in the domain, where every caller reaches it and a test needs no HTTP.
public static PlaceOrderResult placeOrder(Order order) {
    if (order.itemCount() > 100) {
        return PlaceOrderResult.refused("requires-approval");
    }
    return PlaceOrderResult.placed(order);
}
```
