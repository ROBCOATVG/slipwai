```java
/** What the provider returns, in the provider's own shape and vocabulary. Their contract, not ours. */
record StripeCharge(String id, long amount, String currency, String status) { }

/** What the domain understands. */
public sealed interface PaymentResult {
    record Settled(ChargeId chargeId, Money amount) implements PaymentResult { }

    record Failed(String reason) implements PaymentResult { }
}

/**
 * The anticorruption layer: one method, at the boundary, and the only place in this codebase that knows a
 * provider spells currencies in lower case.
 *
 * <p>Without it, `charge.status()` — a String from somebody else's API — spreads through the application,
 * and the day they add a status the compiler has nothing to say about it.
 */
static PaymentResult toPaymentResult(StripeCharge charge) {
    if (!"succeeded".equals(charge.status())) {
        return new PaymentResult.Failed("payment-" + charge.status());
    }
    return new PaymentResult.Settled(
            new ChargeId(charge.id()),
            Money.of(charge.amount(), Currency.valueOf(charge.currency().toUpperCase(Locale.ROOT))));
}
```
