```java
// Pure but NOT domain — it formats for a human, and no business rule changes if the format does.
// Belongs at the driving edge.
static String formatEventDate(Instant date) {
    return DateTimeFormatter.ofPattern("d MMMM yyyy").withZone(ZoneOffset.UTC).format(date);
}

// Pure AND domain — a rule that changes what the system does. Note `now` as a parameter: a rule about
// time that reads the clock itself cannot be tested without freezing global state.
static boolean isPastEvent(Instant eventDate, Instant now) {
    return eventDate != null && eventDate.isBefore(now);
}

// Pure AND domain — a business calculation. "Committed" is a domain concept, and which statuses count
// towards a total is a decision the business owns.
static Money committedTotal(List<GiftItem> items) {
    return items.stream()
            .filter(item -> item.status() != GiftItemStatus.IDEA)
            .map(GiftItem::price)
            .reduce(Money.of(0, Currency.GBP), Money::plus);
}
```
