```java
/**
 * A query function, outside the hexagon: it joins across aggregates because a screen needs one row, and
 * routing that through the write model's ports would mean loading three aggregates to render a table.
 *
 * <p>The rule that keeps this honest: reads may join freely, and may not decide anything.
 */
@ApplicationScoped
public class ParticipantEventQuery {

    private static final String SQL = """
            SELECT e.id, e.title, o.emoji, c.claimed_by
              FROM events e
              JOIN occasions o ON o.event_id = e.id
              LEFT JOIN gift_claims c ON c.event_id = e.id
             WHERE e.id = ?
            """;

    private final DataSource dataSource;

    public List<ParticipantRow> forEvent(String eventId) { }
}
```
