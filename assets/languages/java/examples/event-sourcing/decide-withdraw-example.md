```java
/** One command's rules, in the order they are cheapest to check. Nothing reaches outside its arguments. */
Decision<AccountEvent> decideWithdraw(AccountCommand.Withdraw command, AccountState state) {
    if (!(state instanceof AccountState.Open open)) {
        return Decision.reject("not-open");
    }
    if (!command.amount().isPositive()) {
        return Decision.reject("invalid-amount");
    }
    if (command.amount().currency() != open.balance().currency()) {
        return Decision.reject("currency-mismatch");
    }
    if (command.amount().minorUnits() > open.balance().minorUnits()) {
        return Decision.reject("insufficient-funds");
    }
    return Decision.accept(new AccountEvent.MoneyWithdrawn(command.amount()));
}
```
