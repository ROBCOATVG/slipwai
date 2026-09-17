```java
/**
 * An application-owned repository contract — a driven port. It is declared where it is consumed, so the
 * application's needs shape it rather than the database's schema.
 *
 * <p>The implementation belongs with infrastructure. Nothing in this file names one.
 */
public interface OccasionRepository {

    Optional<Occasion> findById(OccasionId id);

    void save(Occasion occasion);
}
```
