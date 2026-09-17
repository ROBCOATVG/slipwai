```java
// TOO LARGE — User is inside the Occasion, so loading an occasion loads people, and saving one has to
// decide what to do about them.
public record Occasion(
        OccasionId id,
        User organiser,            // embedded entity
        List<User> contributors,   // embedded entities
        List<GiftIdea> giftIdeas) { }

// RIGHT SIZE — only what the budget invariant needs to be enforced.
public record Occasion(
        OccasionId id,
        UserId organiserId,        // a reference: this aggregate does not own users
        Money budget,              // owned: half of the invariant
        List<GiftIdea> giftIdeas) { }   // owned: the other half
```
