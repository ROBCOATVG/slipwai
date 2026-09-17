```java
// The model says which attributes identify something; this is that table, transcribed once.
//
//   - id: S7
//     frames:
//       - type: evt
//         name: SeatClaimed
//         attributes:
//           - { name: seatId,   identifies: seat }
//           - { name: fromHold, identifies: hold }
//           - { name: toHold,   identifies: hold }
//           - { name: claimedAt, type: instant }
//
// Two attributes identifying the same kind is the case worth noticing: a transfer carries two `hold:`
// tags, and a query for either finds the event. A design that mapped one kind to one attribute could
// not express it, and asking such an index "which hold?" has no answer.

/** One identifying attribute: what the payload calls it, and the kind it is a tag for. */
record Identity(String attribute, String kind) {}

/**
 * What each event's payload identifies, keyed by event type.
 *
 * <p>Transcribed from {@code docs/event-model/model.yaml} — the model is the source, this is the copy
 * the store can execute, and {@code make check-model} is what keeps an event's name honest between
 * them.
 */
static final Map<String, List<Identity>> IDENTIFIES = Map.of(
        "SeatClaimed", List.of(
                new Identity("seatId", "seat"),
                new Identity("fromHold", "hold"),
                new Identity("toHold", "hold")),
        "SeatReleased", List.of(new Identity("seatId", "seat")));

/**
 * Every tag an event is findable by: its own stream, plus what it identifies.
 *
 * <p>The stream tag stays, always. It is what makes the index a superset of what the log already had,
 * so a tagged read for {@code TagsOf.streamTag(id)} is the same question as {@code read(id)}, and
 * nothing written against the stream-per-aggregate guard has to change.
 *
 * <p>A missing attribute is skipped rather than thrown on: history is not rewritten, so an event
 * appended before an attribute existed has to keep loading. That is also why this reads the payload by
 * name rather than through a typed shape — it runs over every version of an event ever written.
 */
public static final TagsOf TAGS_OF = event -> {
    List<String> tags = new ArrayList<>();
    tags.add(TagsOf.streamTag(event.streamId()));
    for (Identity identity : IDENTIFIES.getOrDefault(event.type(), List.of())) {
        if (event.payload().get(identity.attribute()) instanceof String value && !value.isBlank()) {
            tags.add(identity.kind() + ":" + value);
        }
    }
    return List.copyOf(tags);
};
```

Wire it in where the store is produced — `new PostgresEventStore(transactions, TAGS_OF)` — and run
`reindexTags` (or `retag`) once against a log that predates it, which is the same rebuild any read model
gets. The tags themselves are never in the model: they are an index over the log, and the model records
only which attributes identify something.
