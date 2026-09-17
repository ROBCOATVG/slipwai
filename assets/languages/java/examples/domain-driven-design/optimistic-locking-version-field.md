```java
/**
 * The version travels beside the aggregate, not inside it.
 *
 * <p>Putting a `version` field on Occasion would make it part of the domain's vocabulary, and nobody in the
 * business has ever asked what version an occasion is at. It is a fact about the row, so it belongs to the
 * layer that reads and writes rows.
 */
public record StoredOccasion(Occasion value, int version) { }
```
