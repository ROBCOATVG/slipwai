/**
 * The process that listens. `make dev` runs this; nothing else in the service binds a socket.
 *
 * It is deliberately the only untested file in `apps/service`. Everything worth asserting about the
 * routes is asserted against the object `buildApp()` returns, dispatched with no socket at all — a test
 * that needs a listening port is an integration test wearing an entry point's clothes, and it proves the
 * one thing this file does rather than anything the app decides. What is left here is composition: build
 * the app, check the environment, bind, and report the address through the app's own logger.
 *
 * Nothing here reads `process.env`. The environment is one schema — `src/config.ts` — checked by
 * `ready()` before anything binds, so `app.config` is typed and a variable this service cannot use stops
 * the process with the variable named instead of surfacing as a 500 an hour later. PORT, HOST and
 * PUBLIC_BASE_URL carry the defaults `.env.example` writes down, and the schema is where they are written.
 *
 * PUBLIC_BASE_URL is reported rather than derived from PORT because behind a proxy or a tunnel the two
 * differ, and the address worth reporting is the one somebody can open.
 */
__STORE_IMPORT__
__FLAGS_IMPORT__
import { startTracing, type Tracing } from './tracing.js';

__STORE_OPEN__
// A flag source, where this project has one, is handed in here and nowhere else — so `buildApp` needs
// no import of a file that a project with nowhere to deploy does not have, and `/api/flags` exists
// exactly where a flag can be declared.
//
// `readiness` is the other thing this file hands over: how to open the store, so `/ready` can ask the
// port whether this service should be sent traffic. The opener rather than the store, because the checked
// environment is `app.config` and that exists once the app has booted — `readiness` calls it there, once.
// A project with no event store passes nothing and gets a route that answers ready with no dependency to
// ask.
const app = buildApp([readiness(__STORE_ARGUMENT__)]__FLAGS_SOURCE__);

let tracing: Tracing | undefined;

// SIGTERM is what `docker compose down` and every orchestrator send, and SIGINT is Ctrl-C. Closing the
// app rather than exiting on the spot lets Fastify finish the requests already in flight; without this a
// demo's last request dies mid-response and reads as a bug in the slice. The tracer goes down after the
// app, in that order, so the spans of the last requests are flushed rather than dropped on the way out.
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => {
    void app.close().then(async () => tracing?.shutdown());
  });
}

try {
  // Where the environment is checked: `ready()` loads the plugins, and `@fastify/env` refuses here —
  // `env/PORT must be number` — rather than letting the service come up and answer wrongly.
  await app.ready();
  // After the environment is checked and before anything can arrive: the endpoint is read off
  // `app.config` rather than `process.env`, and no request exists yet to miss its span. See
  // `src/tracing.ts` for why the exporter is the part that waits to be asked for.
  tracing = startTracing(app.config, app.log);
  await app.listen({ port: app.config.PORT, host: app.config.HOST });
  const address = app.config.PUBLIC_BASE_URL ?? `http://localhost:${app.config.PORT}`;
  app.log.info(
    { service: app.config.OTEL_SERVICE_NAME, exportingTraces: tracing.exporting },
    `service listening on ${address}`,
  );
} catch (error) {
  app.log.error({ err: error }, 'the service could not start');
  process.exitCode = 1;
}
