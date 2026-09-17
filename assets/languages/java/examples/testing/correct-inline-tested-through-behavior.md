```java
// ParticipantView.java
public static ParticipantView load(Items items, EventId eventId, UserId viewer) {
    List<Item> all = items.forEvent(eventId);
    return new ParticipantView(
            all.stream().filter(item -> item.isClaimedBy(viewer)).toList(),
            all.stream().filter(item -> !item.isClaimedBy(viewer)).toList());
}

// The behavioural test for load() covers the filtering; the filters need no test of their own.
@Test
void separatesYourClaimsFromWhatIsStillAvailable() {
    ParticipantView view = ParticipantView.load(items, eventId, viewer);

    assertThat(view.yourClaims()).hasSize(1);
    assertThat(view.available()).hasSize(2);
}
```
