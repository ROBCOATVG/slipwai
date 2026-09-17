```java
/**
 * An always-valid aggregate. The canonical constructor is the only way in, so an Occasion that breaks its
 * own rule cannot exist — not in a test, not after deserialisation, not halfway through an update.
 */
public record Occasion(
        OccasionId id, String name, Money budget, List<GiftIdea> giftIdeas, boolean fundingClosed) {

    public Occasion {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("an occasion needs a name");
        }
        name = name.trim();
        giftIdeas = List.copyOf(giftIdeas);   // defensive copy: the caller's list cannot mutate this one
        if (giftIdeas.stream().anyMatch(idea -> idea.estimatedCost().currency() != budget.currency())) {
            throw new IllegalArgumentException("every gift idea must share the occasion's currency");
        }
        if (totalEstimated(giftIdeas) > budget.minorUnits()) {
            throw new IllegalArgumentException("gift ideas cannot exceed the budget");
        }
    }

    /** The id comes from the edge, so the domain needs no UUID dependency to create one of these. */
    public static Occasion create(OccasionId id, String name, Money budget) {
        return new Occasion(id, name, budget, List.of(), false);
    }

    /** A state transition returns a result: "exceeds budget" is an outcome the caller must handle. */
    public AddGiftIdeaResult addGiftIdea(GiftIdea idea) {
        if (idea.estimatedCost().currency() != budget.currency()) {
            return new AddGiftIdeaResult.Refused("currency-mismatch");
        }
        long remaining = budget.minorUnits() - totalEstimated(giftIdeas);
        if (idea.estimatedCost().minorUnits() > remaining) {
            return new AddGiftIdeaResult.Refused("exceeds-budget");
        }
        List<GiftIdea> updated = new ArrayList<>(giftIdeas);
        updated.add(idea);
        return new AddGiftIdeaResult.Added(
                new Occasion(id, name, budget, updated, fundingClosed));
    }

    private static long totalEstimated(List<GiftIdea> ideas) {
        return ideas.stream().mapToLong(idea -> idea.estimatedCost().minorUnits()).sum();
    }
}

public sealed interface AddGiftIdeaResult {
    record Added(Occasion occasion) implements AddGiftIdeaResult { }

    record Refused(String reason) implements AddGiftIdeaResult { }
}
```
