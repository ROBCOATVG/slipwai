import { createInMemoryCheckpointStore } from '../../src/adapters/driven/checkpoint-store-memory.js';
import { createInMemoryEventStore } from '../../src/adapters/driven/event-store-memory.js';
import { checkpointStoreContract } from './checkpoint-store-contract.js';

/**
 * The checkpoint contract, against the fake. Runs in `make verify` with no Docker, which is the whole
 * reason the in-memory adapters exist. What it cannot prove is two workers genuinely racing for one
 * lease — nothing here runs concurrently — and `make test-integration` is where that is proved.
 */
checkpointStoreContract('the in-memory checkpoint store', async () => {
  const store = createInMemoryEventStore();
  return { store, checkpoints: createInMemoryCheckpointStore(store) };
});
