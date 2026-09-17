/**
 * This process's configuration: one schema over the environment, checked before the service accepts a
 * request.
 *
 * Twelve-factor says configuration comes from the environment, which is a decision about *where* it comes
 * from and says nothing about *when* it is read. Read at the point of use, a missing or misspelt value is
 * discovered by the first request that needs it — in production, by a customer, as a 500 with a stack trace
 * naming something the operator never set. Read here, it is discovered by the process that will not start,
 * and the message names the variable.
 *
 * `@fastify/env` is what does the checking, and it is a TypeBox schema for the reason the routes are: one
 * schema library in the service, producing the types and the validators together, rather than a hand-written
 * shape beside a hand-written check that can disagree with it. What comes out is `app.config`, typed — so a
 * route handler that wants the public base URL reads a `string` and not `process.env.PUBLIC_BASE_URL`, which
 * is `string | undefined` however carefully the deployment was written.
 *
 * `default` is how a value becomes optional: `PORT` unset is 3000, not a refusal. What is deliberately NOT
 * defaulted is anything whose wrong value is worse than its absence — an address this service would
 * otherwise silently publish as its own, a DSN pointing at nothing. Those are optional and *shaped*: absent
 * is fine, present and unusable stops the process.
 *
 * `LOG_LEVEL` and `LOG_FORMAT` are plain strings here rather than the closed sets pino and `loggerOptions`
 * accept, on purpose. A typo in a log variable must never be the thing that stops a deployment, so an
 * unrecognised level falls back to `info` and an unrecognised format to JSON — the two variables this file
 * deliberately does not hold to an enum.
 *
 * Every block below that belongs to one backing service sits inside that service's marked region, so
 * `scripts/backing-services.py` takes the variable away with the adapter that reads it. A variable left
 * behind after its adapter is gone is configuration nobody can act on.
 */
import { type Static, Type } from '@sinclair/typebox';

export const ConfigSchema = Type.Object({
  // The transport's own. HOST defaults to 0.0.0.0 rather than to localhost because this process runs
  // inside a container as often as beside you, and a server bound to 127.0.0.1 in a container is reachable
  // from nothing: the published port answers, the connection is refused, and nothing in the logs says why.
  PORT: Type.Number({ minimum: 1, maximum: 65535, default: 3000 }),
  HOST: Type.String({ minLength: 1, default: '0.0.0.0' }),
  // The address callers reach this service on, which is not derivable from PORT — behind a proxy or a
  // tunnel they differ. Optional, because `main.ts` can fall back to the bound port; shaped, because a
  // value that is not a URL would be printed and pasted and lead nowhere.
  PUBLIC_BASE_URL: Type.Optional(Type.String({ pattern: '^https?://' })),
  LOG_LEVEL: Type.String({ minLength: 1, default: 'info' }),
  LOG_FORMAT: Type.String({ minLength: 1, default: 'json' }),
  // What this service calls itself in a trace. Defaulted to its own package name rather than left to be
  // set, because a service that exports spans as `unknown_service` is a service nobody can find again.
  OTEL_SERVICE_NAME: Type.String({
    minLength: 1,
    default: '__SERVICE_NAME__',
  }),
  // Where to send them, and the one thing that decides whether anything is sent at all (`src/tracing.ts`).
  // Shaped rather than merely optional: present and not a URL stops the process here instead of surfacing
  // as an exporter that silently never connects. The empty string is allowed alongside absent because
  // `.env.example` carries the variable with nothing after the `=`, and an operator turning exporting off
  // by emptying it must not be the thing that stops a deployment — `startTracing` reads both as "off".
  OTEL_EXPORTER_OTLP_ENDPOINT: Type.String({ pattern: '^(https?://.+)?$', default: '' }),
  // Which browser origins may call this service cross-origin, comma-separated. Empty — the default — is
  // same-origin only: no CORS headers are sent to anybody. A wildcard is deliberately not a value this
  // accepts; see the note in `app.ts` for why an allow-list is spelled out.
  CORS_ALLOWED_ORIGINS: Type.String({ default: '' }),
  // backing-service:sqlite:begin
  // Where the event log lives. A path, not a URL: SQLite is a file this process opens, with no server to
  // address.
  EVENT_STORE_PATH: Type.String({ minLength: 1, default: './events.sqlite3' }),
  // backing-service:sqlite:end
  // backing-service:postgres:begin
  // The event store's DSN. Optional rather than required, because the skeleton's entry point opens no
  // store — the slice that wires one is what needs this — but shaped, so a value that is not a Postgres
  // URL is refused at start-up rather than by the first append.
  DATABASE_URL: Type.Optional(Type.String({ pattern: '^postgres(ql)?://' })),
  // backing-service:postgres:end
  // backing-service:keycloak:begin
  // Staff identity. The issuer is what a token is validated against, so a wrong one accepts nothing and
  // says little; refusing the shape here is cheaper than reading it out of a 401.
  OIDC_ISSUER: Type.Optional(Type.String({ pattern: '^https?://' })),
  // backing-service:keycloak:end
  // backing-service:users-keycloak:begin
  // Customer identity: the issuer a customer's bearer token must carry, and the audience this service is.
  USERS_OIDC_ISSUER: Type.Optional(Type.String({ pattern: '^https?://' })),
  USERS_OIDC_AUDIENCE: Type.Optional(Type.String({ minLength: 1 })),
  // backing-service:users-keycloak:end
});

/** This process's configuration, as the schema above defines it. */
export type Config = Static<typeof ConfigSchema>;

declare module 'fastify' {
  interface FastifyInstance {
    /** The validated environment. Populated by `@fastify/env`, so it exists from `ready()` onwards. */
    config: Config;
  }
}
