```java
// application/UserBalanceDeduction.java — the driving port, and the use case behind it.
public interface ForDeductingUserBalances {
    DeductResult deductUserBalance(AuthenticatedPrincipal principal, Money amount);
}

final class UserBalanceDeduction implements ForDeductingUserBalances {

    private final UserRepository users;

    UserBalanceDeduction(UserRepository users) {
        this.users = users;
    }

    @Override
    public DeductResult deductUserBalance(AuthenticatedPrincipal principal, Money amount) {
        Optional<UserRepository.StoredUser> stored = users.findById(principal.userId());
        if (stored.isEmpty()) {
            return new DeductResult.Refused("not-found");
        }
        // The rule is the domain's; the loading, the saving and the conflict are this layer's.
        if (!(deductBalance(stored.get().value(), amount) instanceof DeductResult.Deducted deducted)) {
            return deductBalance(stored.get().value(), amount);
        }
        return users.save(deducted.user(), stored.get().version()) == UserRepository.Saved.SAVED
                ? deducted
                : new DeductResult.Refused("concurrent-change");
    }
}
```
