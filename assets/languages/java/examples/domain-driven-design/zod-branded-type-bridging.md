```java
/**
 * At the trust boundary: raw strings become typed values, and Bean Validation has already rejected what is
 * structurally wrong before this record exists.
 *
 * <p>The wrapper constructors validate again, and that is not redundant — a boundary check protects against
 * bad input, and a constructor check protects against bad code. Both keep working when the other is
 * bypassed.
 */
public record PledgeBody(
        @NotBlank String occasionId,
        @NotBlank String contributorId,
        @Positive long amountMinorUnits,
        @NotNull Currency currency) {

    public PledgeCommand toCommand(PledgeId pledgeId) {
        return new PledgeCommand(
                pledgeId,
                new OccasionId(occasionId),
                new ContributorId(contributorId),
                Money.of(amountMinorUnits, currency));
    }
}

/**
 * Reconstitution from persistence: the same pattern at the other boundary. A driven adapter loads the
 * children alongside the row, so the aggregate arrives whole and its invariants are checked on the way in.
 */
static Occasion toOccasion(ResultSet row, List<GiftIdea> giftIdeas) throws SQLException {
    Currency currency = Currency.valueOf(row.getString("budget_currency"));
    return new Occasion(
            new OccasionId(row.getString("id")),
            row.getString("name"),
            Money.of(row.getLong("budget_minor_units"), currency),
            giftIdeas,
            row.getBoolean("funding_closed"));
}
```
