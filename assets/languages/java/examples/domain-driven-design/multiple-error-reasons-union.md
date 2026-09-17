```java
/**
 * Named reasons rather than a message, so the compiler can help: the HTTP layer switches over this enum
 * exhaustively, and adding a reason forces a decision about its status code.
 */
public sealed interface CreateOrderResult {
    record Created(Order order) implements CreateOrderResult { }

    record Refused(Reason reason) implements CreateOrderResult { }

    enum Reason {
        EMPTY_CART, ITEM_OUT_OF_STOCK, PAYMENT_DECLINED, ADDRESS_INVALID, DAILY_LIMIT_EXCEEDED
    }
}
```
