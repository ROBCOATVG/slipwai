```java
// application/DashboardStatus.java — provider-free policy over rows the query returned.
//
// "Urgent" is a business judgement, so it does not belong in SQL, where nobody would find it and no test
// could reach it without a database. `now` is a parameter for the same reason: a rule about time that
// reads the clock itself cannot be tested at a boundary.
public static DashboardCard toCard(DashboardRow row, Instant now) {
    long daysAway = ChronoUnit.DAYS.between(now, row.eventDate());
    return new DashboardCard(
            row.eventTitle(),
            row.occasionEmoji(),
            daysAway,
            savingsDisplay(row.savedAmount(), row.targetAmount()),
            daysAway < 30);
}
```
