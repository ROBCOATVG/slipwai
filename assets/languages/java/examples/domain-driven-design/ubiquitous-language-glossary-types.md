```java
// Uses the domain's own words, so a conversation with the business and a reading of the code use one
// vocabulary.
public record GiftIdea(
        GiftIdeaId id,
        String description,
        OccasionId occasion,
        Money estimatedCost,
        GiftIdeaStatus status) { }

public enum GiftIdeaStatus { PROPOSED, SELECTED, PURCHASED }

// Technical jargon. Every field needs a translator, and the translation lives in somebody's head.
public record Item(String id, String text, String parentId) { }
```
