```java
/**
 * An entity is identified by its id and not by its fields, so an update returns a new value with the same
 * id rather than mutating one.
 *
 * <p>The generated `with…` shape is deliberate: it goes back through the canonical constructor, so a rename
 * that broke an invariant would fail at the rename rather than at some later read.
 */
public Occasion renamed(String newName) {
    return new Occasion(id, newName, budget, giftIdeas, fundingClosed);
}
```
