```typescript
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
// tags, and a query for either finds the event. A design that mapped one kind to one attribute could not
// express it, and asking such an index "which hold?" has no answer.

/**
 * What each event's payload identifies, keyed by event type: the attribute, and the kind it is a tag for.
 *
 * Transcribed from `docs/event-model/model.yaml` — the model is the source, this is the copy the store can
 * execute, and `make check-model` is what keeps an event's name honest between them.
 */
const IDENTIFIES: Record<string, readonly (readonly [attribute: string, kind: string])[]> = {
  SeatClaimed: [
    ['seatId', 'seat'],
    ['fromHold', 'hold'],
    ['toHold', 'hold'],
  ],
  SeatReleased: [['seatId', 'seat']],
};

/**
 * Every tag this event is findable by: its own stream, plus what it identifies.
 *
 * The stream tag stays, always. It is what makes the index a superset of what the log already had, so
 * `readTagged({ filters: [{ tags: [streamTag(id)] }] })` is the same question as `read(id)`, and nothing
 * written against the stream-per-aggregate guard has to change.
 *
 * A missing attribute is skipped rather than thrown on: history is not rewritten, so an event appended
 * before an attribute existed has to keep loading. That is also why this reads the payload by name rather
 * than through a typed shape — it runs over every version of an event that was ever written.
 */
export const tagsOf: TagsOf = (event) => [
  streamTag(event.streamId),
  ...(IDENTIFIES[event.type] ?? []).flatMap(([attribute, kind]) => {
    const value = event.payload[attribute];
    return typeof value === 'string' && value.length > 0 ? [`${kind}:${value}`] : [];
  }),
];
```

Wire it in where the store is built — `createPostgresEventStore(pool, tagsOf)` — and run `reindexTags` (or
`retag`) once against a log that predates it, which is the same rebuild any read model gets. The tags
themselves are never in the model: they are an index over the log, and the model records only which
attributes identify something.
