```java
// ParticipantFilters.java — a new class with exactly one caller
final class ParticipantFilters {
    static List<Item> claimedBy(List<Item> items, UserId viewer) {
        return items.stream().filter(item -> item.isClaimedBy(viewer)).toList();
    }
}

// ParticipantFiltersTest.java — a test on a seam nobody outside the package can see, so the
// filtering is now pinned twice and can no longer be changed without editing two files.
@Test
void filtersClaims() {
    assertThat(ParticipantFilters.claimedBy(items, viewer)).hasSize(1);
}
```
