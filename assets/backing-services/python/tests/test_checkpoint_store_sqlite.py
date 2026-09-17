"""The checkpoint contract, against SQLite — one file, one connection, real transactions.

This is the cheapest place the transactional checkpoint is genuinely proved: the in-memory
adapter rolls back by restoring a copy, whereas here a failed unit of work is a real ROLLBACK
issued by a real database. `:memory:` because the contract is about behaviour and a fresh
database per test keeps its cases independent.
"""

from contract.checkpoint_store_contract import CheckpointStoreContract

from delivery_starter.adapters.driven.checkpoint_store_sqlite import (
    create_sqlite_checkpoint_store,
)
from delivery_starter.adapters.driven.event_store_sqlite import (
    open_sqlite_event_store,
)
from delivery_starter.application.ports.read_models import (
    CheckpointStore,
)


class TestSqliteCheckpointStore(CheckpointStoreContract):
    def make_stores(self) -> tuple[object, CheckpointStore]:
        store = open_sqlite_event_store(":memory:")
        return store, create_sqlite_checkpoint_store(store)
