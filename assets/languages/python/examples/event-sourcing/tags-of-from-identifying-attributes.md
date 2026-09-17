```python
# The model says which attributes identify something; this is that table, transcribed once.
#
#   - id: S7
#     frames:
#       - type: evt
#         name: SeatClaimed
#         attributes:
#           - { name: seatId,   identifies: seat }
#           - { name: fromHold, identifies: hold }
#           - { name: toHold,   identifies: hold }
#           - { name: claimedAt, type: instant }
#
# Two attributes identifying the same kind is the case worth noticing: a transfer carries two `hold:`
# tags, and a query for either finds the event. A design that mapped one kind to one attribute could
# not express it, and asking such an index "which hold?" has no answer.

#: What each event's payload identifies, keyed by event type: the attribute, and the kind it is a tag
#: for. Transcribed from `docs/event-model/model.yaml` — the model is the source, this is the copy the
#: store can execute, and `make check-model` is what keeps an event's name honest between them.
IDENTIFIES: dict[str, tuple[tuple[str, str], ...]] = {
    "SeatClaimed": (("seatId", "seat"), ("fromHold", "hold"), ("toHold", "hold")),
    "SeatReleased": (("seatId", "seat"),),
}


def tags_of(event: DomainEvent) -> tuple[str, ...]:
    """Every tag this event is findable by: its own stream, plus what it identifies.

    The stream tag stays, always. It is what makes the index a superset of what the log already had,
    so `read_tagged(tagged(stream_tag(id)))` is the same question as `read(id)` and nothing written
    against the stream-per-aggregate guard has to change.

    A missing attribute is skipped rather than raising: history is not rewritten, so an event
    appended before an attribute existed has to keep loading. That is also why this reads the
    payload by name instead of a typed shape — it runs over every version of an event that was ever
    written.
    """
    tags = [stream_tag(event.stream_id)]
    for attribute, kind in IDENTIFIES.get(event.type, ()):
        value = event.payload.get(attribute)
        if isinstance(value, str) and value:
            tags.append(f"{kind}:{value}")
    return tuple(tags)
```

Wire it in where the store is built — `create_postgres_event_store(connection, tags_of)` — and run
`reindex_tags` (or `retag`) once against a log that predates it, which is the same rebuild any read model
gets. The tags themselves are never in the model: they are an index over the log, and the model records
only which attributes identify something.
