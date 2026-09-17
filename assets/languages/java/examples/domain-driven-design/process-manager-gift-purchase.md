```java
/** The phases a gift purchase can be in, each carrying only what that phase knows. */
public sealed interface GiftPurchasePhase {
    record AwaitingPayment(OccasionId occasionId) implements GiftPurchasePhase { }

    record AwaitingShipment(String paymentId) implements GiftPurchasePhase { }

    record Complete(String trackingNumber) implements GiftPurchasePhase { }

    record Failed(String reason) implements GiftPurchasePhase { }
}

/** The process's own state. `processedEventIds` is what makes it safe to be told the same thing twice. */
public record GiftPurchaseProcess(GiftPurchasePhase phase, Set<String> processedEventIds) {

    public GiftPurchaseProcess {
        processedEventIds = Set.copyOf(processedEventIds);
    }
}

public sealed interface ProcessReaction {
    record Applied(GiftPurchaseProcess state, List<GiftPurchaseCommand> commands)
            implements ProcessReaction { }

    record Ignored(GiftPurchaseProcess state, String why) implements ProcessReaction { }
}

/**
 * Apply each event once, and only in the phase that can consume it.
 *
 * <p>Both guards matter and they guard different things. The id check handles redelivery — the same message
 * arriving twice, which a broker guarantees will happen. The phase check handles arrival out of order,
 * which is a different failure and must not be mistaken for a duplicate: silently applying a late
 * `PaymentSucceeded` to a failed process would resurrect it.
 *
 * <p>Every command carries the event id as its idempotency key, so a retry of the reaction does not
 * double-ship the gift.
 */
public static ProcessReaction advance(GiftPurchaseProcess state, GiftPurchaseEvent event) {
    if (state.processedEventIds().contains(event.id())) {
        return new ProcessReaction.Ignored(state, "duplicate");
    }

    Set<String> processed = new LinkedHashSet<>(state.processedEventIds());
    processed.add(event.id());

    return switch (event) {
        case GiftPurchaseEvent.PaymentSucceeded succeeded -> {
            if (!(state.phase() instanceof GiftPurchasePhase.AwaitingPayment)) {
                yield new ProcessReaction.Ignored(state, "out-of-order");
            }
            yield new ProcessReaction.Applied(
                    new GiftPurchaseProcess(
                            new GiftPurchasePhase.AwaitingShipment(succeeded.paymentId()), processed),
                    List.of(new GiftPurchaseCommand.ShipGift(succeeded.paymentId(), event.id())));
        }
        case GiftPurchaseEvent.PaymentFailed failed -> {
            if (!(state.phase() instanceof GiftPurchasePhase.AwaitingPayment awaiting)) {
                yield new ProcessReaction.Ignored(state, "out-of-order");
            }
            yield new ProcessReaction.Applied(
                    new GiftPurchaseProcess(
                            new GiftPurchasePhase.Failed("payment-declined"), processed),
                    List.of(new GiftPurchaseCommand.ReleaseBudgetHold(
                            awaiting.occasionId(), event.id())));
        }
        case GiftPurchaseEvent.GiftShipped shipped -> {
            if (!(state.phase() instanceof GiftPurchasePhase.AwaitingShipment)) {
                yield new ProcessReaction.Ignored(state, "out-of-order");
            }
            yield new ProcessReaction.Applied(
                    new GiftPurchaseProcess(
                            new GiftPurchasePhase.Complete(shipped.trackingNumber()), processed),
                    List.of());
        }
    };
}
```
