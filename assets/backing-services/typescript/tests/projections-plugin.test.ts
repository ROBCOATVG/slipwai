import { randomUUID } from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';

import { createInMemoryCheckpointStore } from '../../src/adapters/driven/checkpoint-store-memory.js';
import { createInMemoryEventStore } from '../../src/adapters/driven/event-store-memory.js';
import type { CommittedEvent, DomainEvent } from '../../src/application/ports/events.js';
import { createCorrelationId, NO_STREAM } from '../../src/application/ports/events.js';
import type { Projection } from '../../src/application/ports/read-models.js';
import type { ProjectionHost } from '../../src/projections-plugin.js';
import { projections } from '../../src/projections-plugin.js';

/**
 * The plugin that runs the catch-up runner — the timer, not the loop.
 *
 * What is worth asserting here is exactly what the plugin contributes: that a pass happens without anybody
 * calling it, and that the host's shutdown hook stops it. The loop itself is `projections.test.ts`.
 *
 * Against a host of its own rather than a real Fastify instance, because the plugin ships with the read
 * side and the read side ships without a transport — a test that imported `fastify` would not run in a
 * project that has no HTTP adapter. What that costs is one thing: whether Fastify itself calls `onClose`.
 * That is Fastify's promise rather than this project's, and the plugin's type is what holds the two
 * together.
 */

/** Just enough of Fastify to register on, and a way to fire the hook the plugin asks for. */
function host(): ProjectionHost & { close(): Promise<void>; failures: unknown[] } {
  const hooks: (() => Promise<void>)[] = [];
  const failures: unknown[] = [];
  return {
    addHook: (_name, hook) => hooks.push(hook),
    log: { error: (details) => failures.push(details.err) },
    close: async () => {
      for (const hook of hooks) await hook();
    },
    failures,
  };
}

class Titles implements Projection {
  rows: string[] = [];
  readonly name = 'titles';

  async apply(events: readonly CommittedEvent[]): Promise<void> {
    this.rows.push(...events.map((event) => event.type));
  }

  async reset(): Promise<void> {
    this.rows = [];
  }
}

const event = (stream: string, type: string): DomainEvent => ({
  type,
  schemaVersion: 1,
  streamId: stream,
  payload: {},
  occurredAt: '2024-01-01T00:00:00.000Z',
  actor: { kind: 'test', id: 'projections' },
  correlationId: createCorrelationId('018f3a2b-6c41-7c9d-9f0e-2a5b7c1d4e84'),
});

describe('the projections plugin', () => {
  it('catches a projection up without anybody calling it', async () => {
    const store = createInMemoryEventStore();
    const view = new Titles();
    const stream = `plugin-${randomUUID()}`;
    await store.append(stream, NO_STREAM, [event(stream, 'Placed')]);

    const app = host();
    await projections(app, {
      store,
      checkpoints: createInMemoryCheckpointStore(store),
      projections: [view],
      everyMs: 5,
    });

    try {
      await vi.waitFor(() => expect(view.rows).toEqual(['Placed']));
    } finally {
      await app.close();
    }
  });

  it('stops passing when the server closes', async () => {
    const store = createInMemoryEventStore();
    const view = new Titles();
    const app = host();
    await projections(app, {
      store,
      checkpoints: createInMemoryCheckpointStore(store),
      projections: [view],
      everyMs: 5,
    });

    await app.close();

    // Appended *after* the close, so a timer still running would pick it up. Nothing does, which is what
    // `onClose` is for: a `setInterval` nobody clears keeps a process alive after SIGTERM.
    const stream = `plugin-${randomUUID()}`;
    await store.append(stream, NO_STREAM, [event(stream, 'Placed')]);
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(view.rows).toEqual([]);
  });
});
