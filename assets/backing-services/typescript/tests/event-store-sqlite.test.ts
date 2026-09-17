import { randomUUID } from 'node:crypto';
import { accessSync, constants, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { openSqliteEventStore } from '../../src/adapters/driven/event-store-sqlite.js';
import {
  createCorrelationId,
  defaultTagsOf,
  NO_STREAM,
} from '../../src/application/ports/events.js';
import { eventStoreContract } from './event-store-contract.js';

/**
 * The shared contract, against SQLite. This runs in `make verify` and needs no Docker — an embedded
 * database is created by the process that opens it, so there is nothing to start and nothing to migrate.
 *
 * `:memory:` here rather than a file, because the contract is about behaviour and a fresh database per
 * test is what keeps its cases independent. The two things a *file* proves — that the log survives the
 * process, and that the database itself refuses to be rewritten — are below, since neither the in-memory
 * fake nor the contract can express them.
 */
eventStoreContract('the SQLite event store', async (tagsOf = defaultTagsOf) =>
  openSqliteEventStore(':memory:', tagsOf),
);

/**
 * Where the database files go: memory when the operating system offers it as a directory, the ordinary
 * temp directory otherwise.
 *
 * Each test below fsyncs about fifteen times — once per schema statement, once per commit, and again for
 * the checkpoint a close performs — because the adapter keeps SQLite's FULL synchronous mode, as an event
 * log must. On a disk that is busy those fsyncs are what the test's time is: ext4 makes one fsync of a tiny
 * file wait for every dirty page on the filesystem, and in CI that is whatever `npm ci` and the jobs beside
 * this one have just written. Three tests that take milliseconds on a laptop have timed out at five seconds
 * on a shared runner, and the disk's latency is not what they are here to prove. `/dev/shm` is memory on
 * Linux, so it is preferred when it can be written; nothing is weakened by that, since the file is still a
 * real file with a WAL beside it, closed and reopened by name. Where there is no such directory — macOS, a
 * container that took it away — the temp directory is what it was.
 */
const RAM_BACKED = '/dev/shm';

const scratchRoot = (): string => {
  try {
    accessSync(RAM_BACKED, constants.W_OK);
    return RAM_BACKED;
  } catch {
    return tmpdir();
  }
};

describe('the SQLite event store, as a durable file', () => {
  const directories: string[] = [];

  const newDatabase = (): string => {
    const directory = mkdtempSync(join(scratchRoot(), 'event-store-sqlite-'));
    directories.push(directory);
    return join(directory, 'events.sqlite3');
  };

  afterEach(() => {
    for (const directory of directories.splice(0))
      rmSync(directory, { recursive: true, force: true });
  });

  // One id for the whole file: these tests are about durability, and a correlation id that changed per
  // event would say these writes belonged to different business transactions, which they do not.
  const correlationId = createCorrelationId(randomUUID());

  const event = (streamId: string, type: string) => ({
    type,
    schemaVersion: 1 as const,
    streamId,
    payload: { step: type },
    occurredAt: '2024-01-01T00:00:00.000Z',
    actor: { kind: 'test', id: 'durability' },
    correlationId,
  });

  it('keeps the log across a close and reopen, which is the whole reason to choose it', async () => {
    const location = newDatabase();

    const first = openSqliteEventStore(location);
    await first.append('order-1', NO_STREAM, [event('order-1', 'Placed')]);
    first.close();

    const reopened = openSqliteEventStore(location);
    try {
      const events = await reopened.read('order-1');
      expect(events.map((committed) => committed.type)).toEqual(['Placed']);
      expect(events[0]?.version).toBe(0);
    } finally {
      reopened.close();
    }
  });

  it('continues the stream at the right version after a restart', async () => {
    const location = newDatabase();

    const first = openSqliteEventStore(location);
    await first.append('order-1', NO_STREAM, [event('order-1', 'Placed')]);
    first.close();

    const reopened = openSqliteEventStore(location);
    try {
      expect(await reopened.append('order-1', 0, [event('order-1', 'Paid')])).toEqual({
        outcome: 'appended',
        version: 1,
      });
      // A caller that has not noticed the restart is still refused, by the same rule as before it.
      expect(await reopened.append('order-1', NO_STREAM, [event('order-1', 'Raced')])).toEqual({
        outcome: 'version-conflict',
        actualVersion: 1,
      });
    } finally {
      reopened.close();
    }
  });

  /**
   * The append-only rule lives in the database, not in the adapter, and this is what says so. A rule the
   * application enforces is a rule the next process to open the file — a migration script, a `sqlite3`
   * shell, a well-meaning fix in production — will not.
   */
  it('refuses to rewrite or erase what has been recorded', async () => {
    const location = newDatabase();
    const store = openSqliteEventStore(location);
    await store.append('order-1', NO_STREAM, [event('order-1', 'Placed')]);
    store.close();

    const { DatabaseSync } = await import('node:sqlite');
    const database = new DatabaseSync(location);
    try {
      expect(() => database.exec("UPDATE events SET event_type = 'Rewritten'")).toThrow(
        /append-only/,
      );
      expect(() => database.exec('DELETE FROM events')).toThrow(/append-only/);
      const rows = database.prepare('SELECT event_type FROM events').all() as unknown as {
        event_type: string;
      }[];
      expect(rows.map((row) => row.event_type)).toEqual(['Placed']);
    } finally {
      database.close();
    }
  });
});
