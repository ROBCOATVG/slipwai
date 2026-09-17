import { createSqliteCheckpointStore } from '../../src/adapters/driven/checkpoint-store-sqlite.js';
import { openSqliteEventStore } from '../../src/adapters/driven/event-store-sqlite.js';
import { checkpointStoreContract } from './checkpoint-store-contract.js';

/**
 * The checkpoint contract, against SQLite — one file, one connection, real transactions.
 *
 * This is the cheapest place the transactional checkpoint is genuinely proved: the in-memory adapter rolls
 * back by restoring a copy, whereas here a failed unit of work is a real ROLLBACK issued by a real
 * database. `:memory:` because the contract is about behaviour and a fresh database per test is what keeps
 * its cases independent.
 */
checkpointStoreContract('the SQLite checkpoint store', async () => {
  const store = openSqliteEventStore(':memory:');
  return { store, checkpoints: createSqliteCheckpointStore(store) };
});
