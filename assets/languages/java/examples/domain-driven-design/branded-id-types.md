```java
/**
 * A record wrapper, not a String. The compiler then refuses to pass an OccasionId where a GiftIdeaId
 * belongs — which is the whole benefit, and it costs one line per identifier.
 */
public record OccasionId(String value) {
    public OccasionId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("an occasion id cannot be blank");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}

public record GiftIdeaId(String value) {
    public GiftIdeaId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("a gift-idea id cannot be blank");
        }
    }
}
```
