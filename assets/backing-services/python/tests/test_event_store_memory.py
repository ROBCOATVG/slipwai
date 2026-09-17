"""The contract, against the fake.

This runs in `make verify` and needs no Docker, which is the whole reason the fake exists.
`make test-integration` runs the same contract against Postgres.
"""

from contract.event_store_contract import EventStoreContract

from delivery_starter.adapters.driven.event_store_memory import (
    create_in_memory_event_store,
)
from delivery_starter.application.ports.events import (
    EventStore,
    TagsOf,
    default_tags_of,
)


class TestInMemoryEventStore(EventStoreContract):
    def make_store(self, tags_of: TagsOf = default_tags_of) -> EventStore:
        return create_in_memory_event_store(tags_of)
