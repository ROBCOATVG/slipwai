```java
// domain/DeductBalance.java — the four rules, extracted, pure, and now testable in microseconds.
public sealed interface DeductResult {
    record Deducted(User user) implements DeductResult { }

    record Refused(String reason) implements DeductResult { }
}

public static DeductResult deductBalance(User user, Money amount) {
    if (!amount.isPositive()) {
        return new DeductResult.Refused("non-positive-amount");
    }
    if (amount.currency() != user.balance().currency()) {
        return new DeductResult.Refused("currency-mismatch");
    }
    if (amount.minorUnits() > user.balance().minorUnits()) {
        return new DeductResult.Refused("insufficient-balance");
    }
    return new DeductResult.Deducted(user.withBalance(user.balance().minus(amount)));
}
```
