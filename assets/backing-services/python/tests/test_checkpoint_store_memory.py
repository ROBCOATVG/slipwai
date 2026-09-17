"""The checkpoint contract, against the fake.

Runs in `make verify` with no Docker, which is the whole reason the in-memory adapters exist.
What it cannot prove is two workers genuinely racing for one lease — nothing here runs
concurrently — and `make test-integration` is where that is proved.
"""

from contract.checkpoint_store_contract import CheckpointStoreContract

from delivery_starter.adapters.driven.checkpoint_store_memory import (
    create_in_memory_checkpoint_store,
)
from delivery_starter.adapters.driven.event_store_memory import (
    create_in_memory_event_store,
)
from delivery_starter.application.ports.read_models import (
    CheckpointStore,
)


class TestInMemoryCheckpointStore(CheckpointStoreContract):
    def make_stores(self) -> tuple[object, CheckpointStore]:
        store = create_in_memory_event_store()
        return store, create_in_memory_checkpoint_store(store)
