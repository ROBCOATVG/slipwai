```java
public enum Currency { GBP, USD, EUR }

/**
 * A value object with its invariant in the canonical constructor, so no code path can produce an invalid
 * one — not reflection, not deserialisation, not a copy.
 *
 * <p>Throwing here means a bug in the calling code. Input from outside is validated at the trust boundary
 * *before* this is reached; if this throws, something bypassed that boundary.
 *
 * <p>`long` minor units rather than `double` or `BigDecimal`: money is a count of pennies, so an integer is
 * the honest representation and a float is the classic way to lose one.
 */
public record Money(long minorUnits, Currency currency) {

    public Money {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("money cannot be negative: " + minorUnits);
        }
        if (currency == null) {
            throw new IllegalArgumentException("money must name a currency");
        }
    }

    public static Money of(long minorUnits, Currency currency) {
        return new Money(minorUnits, currency);
    }

    /** Overflow throws rather than wrapping: a silently negative balance is worse than a crash. */
    public Money plus(Money other) {
        requireSameCurrency(other);
        return new Money(Math.addExact(minorUnits, other.minorUnits), currency);
    }

    public Money minus(Money other) {
        requireSameCurrency(other);
        return new Money(Math.subtractExact(minorUnits, other.minorUnits), currency);
    }

    public boolean isPositive() {
        return minorUnits > 0;
    }

    private void requireSameCurrency(Money other) {
        if (currency != other.currency) {
            throw new IllegalArgumentException("currency mismatch: " + currency + " and " + other.currency);
        }
    }
}
```
