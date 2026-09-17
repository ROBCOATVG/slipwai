```java
// adapters/driven/reporting/DashboardQuery.java — the joins a dashboard needs, and nothing else.
@ApplicationScoped
public class DashboardQuery {

    private static final String SQL = """
            SELECT e.title       AS event_title,
                   e.event_date  AS event_date,
                   o.emoji       AS occasion_emoji,
                   g.saved_amount,
                   g.target_amount,
                   r.name        AS recipient_name
              FROM events e
              JOIN occasions e_o ON ...
              LEFT JOIN savings_goals g ON ...
              JOIN recipients r ON ...
             WHERE e.user_id = ?
            """;

    /** Rows, not view models: shaping them for a screen is a decision, and decisions are not the SQL's. */
    public List<DashboardRow> forUser(String userId) { }
}
```
