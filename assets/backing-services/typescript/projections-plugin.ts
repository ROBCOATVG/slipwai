import type { EventStore } from './application/ports/events.js';
import type { CheckpointStore, Projection } from './application/ports/read-models.js';
import { catchUpEach } from './projections.js';

/**
 * The host this plugin registers on — Fastify, declared structurally rather than imported.
 *
 * Deliberate, and the same reason `FlagSnapshot` in the HTTP adapter is structural: this file ships with the
 * read side, and a project can have a read side and no HTTP adapter at all. An `import` of `fastify` here
 * would not compile in that project — and it is also why this file is not under `adapters/driving/`, where
 * everything belongs to a transport and goes when the transport does. Structural typing means the file is
 * the same in every project, and `app.register(projections, …)` type-checks against the real instance
 * wherever there is one.
 */
export type ProjectionHost = {
  addHook(name: 'onClose', hook: () => Promise<void>): unknown;
  log: { error(details: { err: unknown }, message: string): void };
};

/**
 * What runs an `async` read model: a Fastify plugin, ticking a catch-up pass.
 *
 * A plugin rather than a `setInterval` in the composition root, and the difference is the two things a
 * plugin gets for free. Fastify owns the lifecycle, so `onClose` stops the timer when the server stops —
 * which is what makes `make dev`'s Ctrl-C and a container's SIGTERM leave nothing running. And the app's
 * own logger is the one that reports a failed pass, so this file needs no logging decision of its own.
 *
 * Registered from the composition root, beside the routes, because that is the only place that knows which
 * store this project uses:
 *
 * ```ts
 * const store = openPostgresEventStore(process.env.DATABASE_URL!);
 * const checkpoints = createPostgresCheckpointStore(store);
 * const app = buildApp([registerOrderRoutes(store)]);
 * await app.register(projections, {
 *   store,
 *   checkpoints,
 *   projections: [ordersByCustomer(store)],
 * });
 * ```
 *
 * A project whose read models are all `live` or `inline` registers nothing here, and nothing runs.
 */
export type ProjectionsOptions = Readonly<{
  store: EventStore;
  checkpoints: CheckpointStore;
  projections: readonly Projection[];
  /**
   * How long between passes. This is the lag this project accepts on its async views — the whole cost of
   * that answer, in one number — so it is an option rather than a constant, and `PROJECTIONS_EVERY_MS` is
   * where a deployment turns it down.
   */
  everyMs?: number;
  /**
   * This process's identity as a lease holder. Defaults to a fresh one per registration: two replicas
   * sharing a name would be one owner as far as the lease is concerned, and the holder of a lease may
   * always renew it — so a shared name is two workers both certain they hold it.
   */
  owner?: string;
}>;

export const DEFAULT_EVERY_MS = 1_000;

export async function projections(app: ProjectionHost, options: ProjectionsOptions): Promise<void> {
  const everyMs = options.everyMs ?? Number(process.env.PROJECTIONS_EVERY_MS ?? DEFAULT_EVERY_MS);
  const owner = options.owner ?? `worker-${crypto.randomUUID()}`;
  if (options.projections.length === 0) return;

  // One pass at a time: `running` is what stops a pass slower than the interval from having a second pass
  // pile up behind it. Skipping costs nothing, because the checkpoint means the next tick resumes exactly
  // where this one stopped.
  let running = false;
  const pass = async (): Promise<void> => {
    if (running) return;
    running = true;
    try {
      await catchUpEach(options.store, options.checkpoints, options.projections, {
        owner,
        clock: () => new Date(),
      });
    } catch (failure) {
      // Reported, not rethrown: an unhandled rejection in a timer takes the process down, and a projection
      // that fails every pass would then be a crash loop rather than a stale view. `catchUpEach` has
      // already tried every projection, so nothing is hidden by this.
      app.log.error({ err: failure }, 'projection pass failed');
    } finally {
      running = false;
    }
  };

  const timer = setInterval(() => void pass(), everyMs);
  app.addHook('onClose', async () => {
    clearInterval(timer);
  });
}
