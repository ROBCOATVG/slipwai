import fastifyCors from '@fastify/cors';
import fastifyEnv from '@fastify/env';
import fastifyHelmet from '@fastify/helmet';
import { FastifyOtelInstrumentation } from '@fastify/otel';
import fastifySwagger from '@fastify/swagger';
import type { TypeBoxTypeProvider } from '@fastify/type-provider-typebox';
import { Type } from '@sinclair/typebox';
import Fastify, {
  type FastifyBaseLogger,
  type FastifyError,
  type FastifyInstance,
  type FastifyServerOptions,
  type RawReplyDefaultExpression,
  type RawRequestDefaultExpression,
  type RawServerDefault,
} from 'fastify';

import { type Config, ConfigSchema } from '../../../config.js';
import { traceContextMixin } from '../../../tracing.js';

/**
 * The HTTP driving adapter factory.
 *
 * A driving adapter parses untrusted input into typed commands, calls a use case, and renders the
 * outcome. It holds **no business rules** and makes **no authorisation decision** — authorisation is
 * decided inside the use case, because a rule enforced in a route handler is a rule that a second entry
 * point will not enforce.
 *
 * "Parses untrusted input" is the schema's job and not a handler's. Every route here declares what it
 * accepts and what it answers with, and the framework compiles both: the request is validated before the
 * handler runs, and the response is serialised *through* the schema, so a field the contract does not
 * name cannot leave this process however a handler is later edited. A route with no schema accepts
 * anything and returns whatever it happens to hold, which is the state this replaces.
 *
 * Status mapping belongs here precisely because the domain speaks business vocabulary:
 *   400 — schema failure: the shape is wrong
 *   422 — business rejection: the shape is fine, the rule says no
 *   404 — not found, INCLUDING another tenant's resource, so existence is not leaked
 *   409 — a conflict the caller may retry differently, which is where a version conflict from the event
 *         store surfaces: the store returns it as a value, and this is the layer that gives it a status
 */

/**
 * This service's Fastify instance, with TypeBox reading the schemas.
 *
 * The type provider is what makes a declared schema and a handler's types the same fact: `request.body`
 * is typed from the `body` schema, and a handler returning something the `response` schema does not allow
 * is a compile error rather than a field silently dropped at run time.
 */
export type App = FastifyInstance<
  RawServerDefault,
  RawRequestDefaultExpression,
  RawReplyDefaultExpression,
  FastifyBaseLogger,
  TypeBoxTypeProvider
>;

export type RouteRegistrar = (app: App) => void;

/**
 * Just enough of the flag reader's `FlagSource` for this file to serve one, declared structurally rather
 * than imported.
 *
 * Deliberate: `src/flags.ts` exists only in a project with somewhere to deploy, so an import of it here
 * would not compile in one without. Structural typing means this file needs no import, stays the same in
 * every project, and is exercised by its own tests either way — while a project with no flags simply never
 * passes a source, and then has no `/api/flags` route rather than an inert one.
 */
export type FlagSnapshot = { snapshot(): Record<string, string> };

/** The levels pino accepts. Anything else in `LOG_LEVEL` is a typo, and a typo is not a reason to refuse. */
const LEVELS = ['trace', 'debug', 'info', 'warn', 'error', 'fatal', 'silent'] as const;

/**
 * How this process logs, decided from the environment and nowhere else.
 *
 * On, and structured, from the first run. The alternative — Fastify's `logger: false` — is not "no
 * logging", it is a sink: `app.log.error` still exists and still returns, so a projection that dies in
 * the projections plugin reports its reason to nothing and the first anyone knows is a view that
 * stopped moving. A service that cannot say why it failed is a service nobody can operate.
 *
 * JSON by default, because that is what a log shipper reads. `LOG_FORMAT=pretty` — which `make dev`
 * sets — reformats the same records as one readable line each, for a person watching a terminal.
 *
 * That reformatting is fifteen lines here rather than the `pino-pretty` dependency it would otherwise
 * be, and deliberately so: a starter should not spend a project's first dependency on making its own
 * development output legible, and this is the whole of what is wanted. Swap in `pino-pretty` the day a
 * project wants colours and filters — it is a `transport` in place of this `stream`, and nothing else
 * in the service changes.
 *
 * Read straight from `process.env` rather than from `app.config`, because the logger is built before the
 * app that validates the environment is — which is also why an unrecognised level falls back to `info`
 * instead of letting pino throw: the one thing worse than a mis-set log level is a process that will not
 * start and cannot say why.
 *
 * Silent under Vitest, which sets `NODE_ENV=test`, so a suite is not a wall of request lines. A test
 * that wants to assert on a log line sets `LOG_LEVEL` and gets one.
 *
 * `mixin` is what puts `trace_id` and `span_id` on every record written while a request is in flight —
 * a function rather than a fixed field because the span exists only for the duration of a request, and
 * this logger is built once for the life of the process. A log line nobody can tie back to a request is
 * the reason an incident takes an afternoon; see `src/tracing.ts`.
 */
export function loggerOptions(): NonNullable<FastifyServerOptions['logger']> {
  const asked = process.env.LOG_LEVEL ?? (process.env.NODE_ENV === 'test' ? 'silent' : 'info');
  const level = (LEVELS as readonly string[]).includes(asked) ? asked : 'info';
  const mixin = traceContextMixin;
  return process.env.LOG_FORMAT === 'pretty'
    ? { level, mixin, stream: prettyStream() }
    : { level, mixin };
}

/** pino's numeric levels, back to the names a person reads. */
const LEVEL_NAMES: Record<number, string> = {
  10: 'trace',
  20: 'debug',
  30: 'info',
  40: 'warn',
  50: 'error',
  60: 'fatal',
};

/**
 * A destination that turns each JSON record back into one line: time, level, message, and whatever else
 * the record carried. `pid` and `hostname` are dropped — in a terminal they are the same two values on
 * every line — and a record that will not parse is passed through untouched rather than swallowed.
 */
export function prettyStream(): { write(line: string): void } {
  return {
    write(line: string): void {
      try {
        // `pid` and `hostname` are named only so the rest pattern leaves them out of the line.
        const {
          level,
          time,
          msg,
          pid: _pid,
          hostname: _host,
          ...rest
        } = JSON.parse(line) as Record<string, unknown>;
        const at = new Date(typeof time === 'number' ? time : Date.now())
          .toISOString()
          .slice(11, 23);
        const name = LEVEL_NAMES[level as number] ?? String(level);
        const extra = Object.keys(rest).length > 0 ? ` ${JSON.stringify(rest)}` : '';
        process.stdout.write(
          `${at} ${name.toUpperCase().padEnd(5)} ${String(msg ?? '')}${extra}\n`,
        );
      } catch {
        process.stdout.write(line);
      }
    },
  };
}

/**
 * A route that takes no query string says so, rather than saying nothing.
 *
 * `additionalProperties: false` with Fastify's `removeAdditional` turned off below is what makes
 * `?statsu=1` a 400 instead of a silently ignored parameter. A caller who misspells a filter and gets a
 * 200 back has been told their filter worked.
 */
const NoQuery = Type.Object({}, { additionalProperties: false });

/** What `/health` answers. Declared, so the probe's contract is in the published document like any other. */
const HealthResponse = Type.Object({ status: Type.Literal('ok') });

/** What `/ready` answers when the driven ports answer: the service will take traffic. */
const ReadyResponse = Type.Object({ status: Type.Literal('ready') });

/**
 * And what it answers when one does not. `reason` is a *category* and never the driver's own message: a
 * declared schema is what keeps it that way, because the response is serialised through this and a
 * connection string a later edit reaches for cannot leave the process.
 */
const UnreadyResponse = Type.Object({
  status: Type.Literal('unready'),
  reason: Type.Literal('eventStore'),
});

/** What `/api/flags` answers: this environment's flags, by key. */
const FlagsResponse = Type.Record(Type.String(), Type.String());

export function buildApp(registrars: readonly RouteRegistrar[] = [], flags?: FlagSnapshot): App {
  const app = Fastify({
    logger: loggerOptions(),
    // Fastify's default is `removeAdditional: true`, which quietly deletes anything a schema did not
    // name before the handler sees it. That turns a misspelt field into a missing one and a caller's
    // mistake into this service's silent data loss, so a request that carries something no route declares
    // is refused instead.
    ajv: { customOptions: { removeAdditional: false } },
  }).withTypeProvider<TypeBoxTypeProvider>();

  // The environment, checked once. `app.config` is typed from `ConfigSchema` and populated by `ready()`,
  // so a variable this service cannot use stops the process instead of surfacing as a 500 later.
  void app.register(fastifyEnv, { schema: ConfigSchema, confKey: 'config' });

  // One span per request, continuing whatever `traceparent` the caller sent. Registered here rather than
  // patched onto the framework at load time (`registerOnInitialization`), because this app is built by a
  // function that tests call directly: a plugin on the instance is instrumentation a test can drive, and
  // an import-time hook is instrumentation that only exists when the process was started a particular way.
  //
  // The tracer this plugin asks for is a proxy until `startTracing` registers a provider — `src/main.ts`
  // does that between `ready()` and `listen()` — so nothing here depends on the order the two happen in.
  void app.register(new FastifyOtelInstrumentation().plugin());

  /**
   * The response headers a browser is told to enforce, and who is allowed to ask for them at all.
   *
   * Two plugins rather than a hand-written pair, because both are specifications with edge cases — a
   * preflight that has to answer before any route runs, a `Vary: Origin` without which a shared cache
   * serves one origin's response to another — and neither is a place to be inventive.
   *
   * ── Helmet: the defaults, on ────────────────────────────────────────────────────────────────────────
   * `nosniff`, `frame-ancestors`, a referrer policy, HSTS. For a JSON API most of them are cheap
   * insurance rather than the load-bearing control, and the one that matters is the one nobody thinks
   * about: the day a route starts returning HTML — an error page, a hosted callback, a rendered receipt —
   * the headers are already there. Turning them on later is a change nobody remembers to make.
   *
   * ── CORS: an allow-list, never a wildcard ───────────────────────────────────────────────────────────
   * Empty is the default and means *no* CORS headers are sent to anybody, which is same-origin only. That
   * is the right answer for `make dev` and `make demo`: the browser app is served from its own origin and
   * the dev server forwards `/api` here, so nothing is cross-origin and nothing needs permitting.
   *
   * `CORS_ALLOWED_ORIGINS` names the exact origins that may, comma-separated. There is deliberately no
   * `*`: a wildcard and credentials cannot be combined at all, and a wildcard without them still hands
   * every page on the internet a reader for whatever this service will answer unauthenticated. An origin
   * this service does not recognise gets a reply with no `access-control-allow-origin` header, and the
   * browser refuses it — which is the enforcement, since CORS is a rule browsers apply and not one this
   * process can apply on their behalf.
   *
   * Read through `app.config` at request time rather than captured here, so the value is the checked one.
   */
  void app.register(fastifyHelmet);
  void app.register(fastifyCors, {
    origin: (origin, callback) => {
      callback(
        null,
        origin !== undefined && allowedOrigins(app.config.CORS_ALLOWED_ORIGINS).includes(origin),
      );
    },
  });

  // The API document, built from the same schemas the routes are validated with — so it cannot describe
  // a contract this service does not actually enforce. Served at `/openapi.json` below.
  void app.register(fastifySwagger, {
    openapi: {
      info: { title: '__SERVICE_NAME__', version: '0.1.0' },
    },
  });

  /**
   * One way to fail a bad request, whichever route found it.
   *
   * The framework raises every schema failure — body, query string, path parameter, header — as one kind
   * of error, so this is the only place that has to turn one into a status and a body. A handler that
   * checks a shape by hand is a second way to fail, with a second body shape, and callers end up parsing
   * both.
   */
  // `error` is annotated because the type provider leaves the handler's own inference with nothing to go
  // on; `FastifyError` is what the framework actually passes, and `validation` is the field that says a
  // schema — rather than the application — is what refused this request.
  app.setErrorHandler((error: FastifyError, _request, reply) => {
    if (error.validation !== undefined) {
      reply.code(400).send(schemaFailure(error.validation));
      return;
    }
    reply.send(error);
  });

  /**
   * Fastify's default 404 echoes the request path: `{"message":"Route POST:/register/tok-live-… not found"}`.
   *
   * That puts whatever the URL carried into a response body, and from there into every proxy and access log
   * along the way. For any project whose URLs carry a credential — a no-login link, a password-reset path, a
   * signed download — the 404 is the disclosure, and it discloses to whoever probed for it.
   *
   * Three lines rather than a note in the docs, in a skeleton that is otherwise deliberately bare, because
   * this is a **default correction and not a feature**. What this file omits — authentication, CORS, rate
   * limiting, body limits — are choices a project makes. Echoing back the path it was given is not a choice
   * anyone makes deliberately, and the alternative is telling every generated project to write the same
   * three lines, which is the thing a starter exists to avoid.
   *
   * It is also what makes the 404 above honest. That mapping already promises another tenant's resource is
   * indistinguishable from one that never existed; a handler that reflects the path undercuts the promise
   * the comment makes.
   *
   * The reply says nothing the caller did not already know: no path, no method, no hint whether the route
   * exists under a different verb.
   */
  app.setNotFoundHandler((_request, reply) => {
    reply.code(404).send({ error: 'notFound' });
  });

  /**
   * Every route is declared inside `after`, and that is not a style choice.
   *
   * `register` is deferred: the plugin above — and the hook it uses to notice a route — is loaded when the
   * app boots, which is after this function has returned. A route declared before that hook exists is a
   * route the document never hears about, and the failure is silent: `/openapi.json` answers 200 with an
   * empty `paths`. `after` runs once the plugins registered so far have loaded, in this same instance, so
   * the routes below and the ones a slice hands in are both in the document.
   */
  app.after(() => {
    // Liveness: this process is up and answering. Unconditional on purpose — it asks nothing of any
    // dependency, because a liveness probe that fails when a database is unreachable gets the process
    // restarted when the only thing wrong is somewhere else. What gates traffic is `/ready`, which
    // `readiness()` below registers.
    app.get(
      '/health',
      { schema: { querystring: NoQuery, response: { 200: HealthResponse } } },
      async () => ({ status: 'ok' }) as const,
    );

    /**
     * This service's own API contract, as the routes actually declare it.
     *
     * A published document rather than a page: a browser app generates its client from this, a test
     * asserts against it, and `make verify` never has to start a browser to know the contract changed.
     * `hide` keeps the document out of the document.
     */
    app.get('/openapi.json', { schema: { hide: true } }, async () => app.swagger());

    /**
     * This environment's feature flags, for the browser app — which cannot read them itself.
     *
     * Under `/api` because that is this service's product surface and a browser calls it; `/health` sits
     * outside it because it is a probe. `vite.config.ts` forwards `/api` with the prefix intact and
     * CloudFront's `/api/*` behaviour rewrites nothing, so this is the one path in both places.
     *
     * Registered only when a source was passed, so a project with nowhere to declare a flag has no route
     * here rather than one that always answers `{}`. `no-store` because the answer is what the environment
     * is set to *now*: a flipped flag that a cache still hides is the flip looking broken.
     */
    if (flags !== undefined) {
      app.get(
        '/api/flags',
        { schema: { querystring: NoQuery, response: { 200: FlagsResponse } } },
        async (_request, reply) => {
          reply.header('cache-control', 'no-store');
          return flags.snapshot();
        },
      );
    }

    for (const register of registrars) register(app);
  });

  return app;
}

/**
 * Just enough of the event-store port for this file to probe one, declared structurally rather than
 * imported — the same reason `FlagSnapshot` above is structural, and a stronger one: this file is the HTTP
 * adapter of *any* project on this transport, and a project on the standard profile has no event store and
 * no port to import.
 *
 * `head()` and nothing else. It is the cheapest honest question the port already answers — the last global
 * position in the log, or zero when it is empty — so a readiness probe needs no method of its own and the
 * port is not widened to carry one. A store that cannot answer it cannot serve a request either.
 */
export type ReadinessProbe = { head(): Promise<number> };

/**
 * `/ready`: whether this service should be sent traffic, which is a different question from whether it is
 * running.
 *
 * `/health` is liveness — the process is up and answering — and it is deliberately unconditional: a probe
 * that goes red because a dependency is down gets the process killed rather than taken out of the pool.
 * This one asks the driven port the service cannot work without, **through the port** and never through an
 * adapter, so an event store that has gone away is reported as "do not send me traffic" instead of staying
 * invisible until the first real request fails.
 *
 * A registrar rather than a route inside `buildApp`, because the store is the composition root's to open
 * and hand over, and `buildApp` is shared with every project on this transport — including the ones with no
 * store to hand it. Those call `readiness()` with nothing and get a route that answers ready with no
 * dependency to ask, which is the truth for a project whose only driven port is the clock. Being a
 * registrar also puts it inside `after`, so it reaches `/openapi.json` like every other route.
 *
 * The failure reason is logged and not sent. A caller learns the category and no more: what is wrong with
 * this service's dependencies is not something an unauthenticated prober needs, and a connection string in
 * a driver's error message is exactly what would otherwise end up in one — which is the whole reason the
 * 503 body is a declared schema rather than whatever the handler happens to hold.
 */
export type OpenStore = (config: Config) => ReadinessProbe;

export function readiness(open?: OpenStore): RouteRegistrar {
  return (app) => {
    // Opened here, once, rather than before `buildApp`: `app.config` is the checked environment and
    // `@fastify/env` populates it as the app boots, which is inside this `after` and not before it. The
    // composition root still decides *what* is opened; this is only where the environment exists.
    const store = open?.(app.config);
    app.get(
      '/ready',
      { schema: { querystring: NoQuery, response: { 200: ReadyResponse, 503: UnreadyResponse } } },
      async (_request, reply) => {
        reply.header('cache-control', 'no-store');
        if (store === undefined) return { status: 'ready' } as const;
        try {
          await store.head();
          return { status: 'ready' } as const;
        } catch (error) {
          app.log.error({ err: error }, 'the event store did not answer; reporting not ready');
          reply.code(503);
          return { status: 'unready', reason: 'eventStore' } as const;
        }
      },
    );
  };
}

/**
 * The origins `CORS_ALLOWED_ORIGINS` names, as a list.
 *
 * Whitespace around a comma is dropped and an empty entry is not an origin — a trailing comma in a
 * deployment's environment must not become a permission for the empty string, which is what an origin
 * header carries when a request has none.
 */
export function allowedOrigins(raw: string): string[] {
  return raw
    .split(',')
    .map((origin) => origin.trim())
    .filter((origin) => origin !== '');
}

/**
 * One schema failure, as a caller reads it — the single 400 body in this service.
 *
 * The offending value is deliberately absent: a validation error on a field holding a token or a password
 * must not quote it back. What is reported is where the failure was and what the rule said, which is the
 * only part a caller can act on.
 */
export type SchemaIssue = {
  instancePath?: string;
  message?: string;
  params?: { missingProperty?: string; additionalProperty?: string };
};

export function schemaFailure(issues: readonly SchemaIssue[] | undefined) {
  const first = issues?.[0];
  const path = first?.instancePath ?? '';
  const params = first?.params ?? {};
  // A missing or unexpected property is reported against the object that should or should not have had
  // it, so the path alone would say `(root)` for the two failures a caller most often makes.
  const named = params.missingProperty ?? params.additionalProperty;
  const prefix = path === '' ? '' : `${path.replace(/^\//, '').replaceAll('/', '.')}.`;
  return {
    error: 'schemaValidationFailed',
    field: named !== undefined ? `${prefix}${named}` : prefix.replace(/\.$/, '') || '(root)',
    message: first?.message ?? 'invalid request body',
  };
}
