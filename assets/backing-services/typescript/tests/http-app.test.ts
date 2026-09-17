import { Type } from '@sinclair/typebox';
import { describe, expect, it } from 'vitest';

import {
  allowedOrigins,
  buildApp,
  loggerOptions,
  prettyStream,
  type RouteRegistrar,
  readiness,
  schemaFailure,
} from '../../src/adapters/driving/http/app.js';
import { traceContextMixin } from '../../src/tracing.js';

/**
 * Edge tests: the outermost surface, exercised through the framework rather than around it.
 *
 * `app.inject()` runs a real request through the real router with no socket, so these stay in `make
 * verify` — an entry-point test that needs a listening port is an integration test wearing the wrong name.
 */
describe('how the service logs', () => {
  /**
   * The environment decides, and the default is a shipper's format rather than a person's. Asserted
   * because `logger: false` — the state this replaced — is the one setting that makes every later
   * `app.log.error` a no-op, and nothing else in the suite would notice it coming back.
   */
  const withEnvironment = <T>(changes: Record<string, string | undefined>, read: () => T): T => {
    const before = { ...process.env };
    try {
      Object.assign(process.env, changes);
      for (const [name, value] of Object.entries(changes))
        if (value === undefined) delete process.env[name];
      return read();
    } finally {
      process.env = before;
    }
  };

  it('logs JSON at info by default, with the trace context on every record', () => {
    // `mixin` is what puts `trace_id` and `span_id` on a line written during a request; it is asserted
    // here rather than only in `tracing.test.ts` because it is part of how this service logs at all.
    expect(
      withEnvironment(
        { NODE_ENV: undefined, LOG_LEVEL: undefined, LOG_FORMAT: undefined },
        loggerOptions,
      ),
    ).toEqual({ level: 'info', mixin: traceContextMixin });
  });

  it('reformats each record as one line when the environment asks for a terminal, as `make dev` does', () => {
    const options = withEnvironment({ NODE_ENV: undefined, LOG_FORMAT: 'pretty' }, loggerOptions);

    expect(options).toMatchObject({ level: 'info' });
    expect(typeof (options as { stream: { write: unknown } }).stream.write).toBe('function');
  });

  it('writes a readable line for a record and passes anything unparseable through', () => {
    const written: string[] = [];
    const stdout = process.stdout.write.bind(process.stdout);
    process.stdout.write = ((line: string) => {
      written.push(line);
      return true;
    }) as typeof process.stdout.write;
    try {
      const stream = prettyStream();
      stream.write(
        JSON.stringify({
          level: 50,
          time: 0,
          msg: 'the pass failed',
          pid: 1,
          hostname: 'h',
          view: 'orders',
        }),
      );
      stream.write('not json\n');
    } finally {
      process.stdout.write = stdout;
    }

    expect(written[0]).toBe('00:00:00.000 ERROR the pass failed {"view":"orders"}\n');
    expect(written[0]).not.toContain('hostname');
    expect(written[1]).toBe('not json\n');
  });

  it('is silent under the test runner unless a level is asked for', () => {
    expect(withEnvironment({ NODE_ENV: 'test', LOG_LEVEL: undefined }, loggerOptions)).toEqual({
      level: 'silent',
      mixin: traceContextMixin,
    });
    expect(withEnvironment({ NODE_ENV: 'test', LOG_LEVEL: 'debug' }, loggerOptions)).toEqual({
      level: 'debug',
      mixin: traceContextMixin,
    });
  });
});

describe('the HTTP entry point', () => {
  it('reports readiness', async () => {
    const app = buildApp();
    try {
      const response = await app.inject({ method: 'GET', url: '/health' });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ status: 'ok' });
    } finally {
      await app.close();
    }
  });

  /**
   * The framework default would answer `{"message":"Route GET:/orders/tok-live-abc123 not found"}`, putting
   * whatever the URL carried into a response body and every access log downstream. This asserts the
   * correction rather than the default, because it is the kind of regression a framework upgrade
   * reintroduces silently.
   */
  it('does not echo the requested path back on a 404', async () => {
    const app = buildApp();
    try {
      const response = await app.inject({ method: 'GET', url: '/orders/tok-live-abc123' });

      expect(response.statusCode).toBe(404);
      expect(response.json()).toEqual({ error: 'notFound' });
      expect(response.body).not.toContain('tok-live-abc123');
      expect(response.body).not.toContain('/orders');
    } finally {
      await app.close();
    }
  });

  it('does not reveal that a path exists under a different method', async () => {
    const app = buildApp();
    try {
      const response = await app.inject({ method: 'POST', url: '/health' });

      expect(response.statusCode).toBe(404);
      expect(response.json()).toEqual({ error: 'notFound' });
    } finally {
      await app.close();
    }
  });

  it('registers the routes it is given, and holds none of its own', async () => {
    const app = buildApp([
      (instance) => {
        instance.get('/orders/:id', async () => ({ id: 'order-1' }));
      },
    ]);
    try {
      const response = await app.inject({ method: 'GET', url: '/orders/order-1' });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ id: 'order-1' });
    } finally {
      await app.close();
    }
  });

  it("serves this environment's flags to the browser app when it is given a source", async () => {
    // A browser cannot read this environment, so the service answers for it. `snapshot()` is the reader's
    // second question and this route is the only caller of it.
    const app = buildApp([], { snapshot: () => ({ 'checkout-v2': 'on' }) });
    try {
      const response = await app.inject({ method: 'GET', url: '/api/flags' });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ 'checkout-v2': 'on' });
      // The answer is what the environment is set to *now*: a flipped flag a cache still hides is the
      // flip looking broken.
      expect(response.headers['cache-control']).toBe('no-store');
    } finally {
      await app.close();
    }
  });

  it('has no flags route at all when it is given no source', async () => {
    // `--target none` has nowhere to declare a flag, so this route is absent rather than answering `{}` —
    // an endpoint that always returns nothing reads as a capability the project does not have.
    const app = buildApp();
    try {
      const response = await app.inject({ method: 'GET', url: '/api/flags' });

      expect(response.statusCode).toBe(404);
      expect(response.json()).toEqual({ error: 'notFound' });
    } finally {
      await app.close();
    }
  });

  /**
   * Readiness, which is the probe that decides whether this service is sent traffic.
   *
   * The fake is written here, by hand, and that is the rule rather than an accident: a mocking framework
   * would let this suite assert that `head` was *called*, which proves nothing about what the route does
   * with the answer. What matters is the two answers the port can give and the two statuses they become.
   */
  //
  // What is handed in is an *opener*, because that is what the composition root hands over: the store is
  // opened from the checked environment, which exists only once the app has booted.
  const failing = () => ({
    head: async (): Promise<number> => Promise.reject(new Error('connection refused')),
  });
  const empty = () => ({ head: async (): Promise<number> => 0 });

  it('is ready when the event store answers', async () => {
    const app = buildApp([readiness(empty)]);
    try {
      const response = await app.inject({ method: 'GET', url: '/ready' });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ status: 'ready' });
    } finally {
      await app.close();
    }
  });

  it('is not ready, and says no more than the category, when the event store does not answer', async () => {
    const app = buildApp([readiness(failing)]);
    try {
      const response = await app.inject({ method: 'GET', url: '/ready' });

      expect(response.statusCode).toBe(503);
      expect(response.json()).toEqual({ status: 'unready', reason: 'eventStore' });
      // The driver's own message — which is where a connection string ends up — stays in the log.
      expect(response.body).not.toContain('connection refused');
    } finally {
      await app.close();
    }
  });

  it('is ready with nothing to ask when the project has no store', async () => {
    // Liveness is still liveness: `/health` answers whatever the dependencies are doing.
    const app = buildApp([readiness()]);
    try {
      expect((await app.inject({ method: 'GET', url: '/ready' })).json()).toEqual({
        status: 'ready',
      });
      expect((await app.inject({ method: 'GET', url: '/health' })).json()).toEqual({
        status: 'ok',
      });
    } finally {
      await app.close();
    }
  });

  it('reports a schema failure in one shape, whichever route found it', () => {
    expect(
      schemaFailure([{ instancePath: '/customer/email', message: 'must match format "email"' }]),
    ).toEqual({
      error: 'schemaValidationFailed',
      field: 'customer.email',
      message: 'must match format "email"',
    });
    // The two failures a caller most often makes are reported against the object that should or should
    // not have had the field, so the path alone would say `(root)` for both.
    expect(
      schemaFailure([
        {
          instancePath: '/customer',
          message: "must have required property 'email'",
          params: { missingProperty: 'email' },
        },
      ]),
    ).toEqual({
      error: 'schemaValidationFailed',
      field: 'customer.email',
      message: "must have required property 'email'",
    });
    expect(schemaFailure(undefined)).toEqual({
      error: 'schemaValidationFailed',
      field: '(root)',
      message: 'invalid request body',
    });
  });
});

/**
 * The schema is the contract: the framework validates every request against it, serialises every response
 * through it, and publishes it. These assert all three, because each one silently stops being true in a
 * different way — a route declared with no schema, a handler that returns more than it promised, and a
 * plugin registered after the first route so the document comes out empty.
 */
describe('the API contract', () => {
  /** A slice's route, declared the way every route in this service is. */
  const orders: RouteRegistrar = (app) => {
    app.post(
      '/orders',
      {
        schema: {
          body: Type.Object(
            { sku: Type.String({ minLength: 1 }) },
            { additionalProperties: false },
          ),
          response: { 201: Type.Object({ id: Type.String() }) },
        },
      },
      async (request, reply) => {
        reply.code(201);
        // Deliberately more than the schema names, to prove the serialiser is what decides.
        return { id: `order-for-${request.body.sku}`, internalCost: 42 } as { id: string };
      },
    );
  };

  it("refuses a body that does not match the route's schema, in the one 400 shape", async () => {
    const app = buildApp([orders]);
    try {
      const response = await app.inject({ method: 'POST', url: '/orders', payload: {} });

      expect(response.statusCode).toBe(400);
      expect(response.json()).toEqual({
        error: 'schemaValidationFailed',
        field: 'sku',
        message: "must have required property 'sku'",
      });
    } finally {
      await app.close();
    }
  });

  /**
   * Fastify's default is to delete anything a schema did not name before the handler sees it, which turns
   * a caller's misspelt field into a missing one and this service's silent data loss. `removeAdditional`
   * is off for that reason, and this is what would notice it coming back.
   */
  it('refuses a field the route did not declare rather than dropping it', async () => {
    const app = buildApp([orders]);
    try {
      const response = await app.inject({
        method: 'POST',
        url: '/orders',
        payload: { sku: 'sku-1', discuont: 10 },
      });

      expect(response.statusCode).toBe(400);
      expect(response.json()).toMatchObject({ error: 'schemaValidationFailed', field: 'discuont' });
    } finally {
      await app.close();
    }
  });

  it('refuses a query string parameter no route declares', async () => {
    const app = buildApp();
    try {
      const response = await app.inject({ method: 'GET', url: '/health?statsu=1' });

      expect(response.statusCode).toBe(400);
      expect(response.json()).toMatchObject({ error: 'schemaValidationFailed', field: 'statsu' });
    } finally {
      await app.close();
    }
  });

  it('answers with what the response schema names and nothing else', async () => {
    const app = buildApp([orders]);
    try {
      const response = await app.inject({
        method: 'POST',
        url: '/orders',
        payload: { sku: 'sku-1' },
      });

      expect(response.statusCode).toBe(201);
      expect(response.json()).toEqual({ id: 'order-for-sku-1' });
      expect(response.body).not.toContain('internalCost');
    } finally {
      await app.close();
    }
  });

  it('publishes the document, and it carries the routes a slice registered', async () => {
    const app = buildApp([orders], { snapshot: () => ({ 'checkout-v2': 'on' }) });
    try {
      const response = await app.inject({ method: 'GET', url: '/openapi.json' });

      expect(response.statusCode).toBe(200);
      const document = response.json() as { paths: Record<string, unknown> };
      expect(Object.keys(document.paths).sort()).toEqual(['/api/flags', '/health', '/orders']);
      // The document does not describe itself.
      expect(document.paths['/openapi.json']).toBeUndefined();
    } finally {
      await app.close();
    }
  });
});

describe('the environment this process was given', () => {
  const withEnvironment = async <T>(
    changes: Record<string, string | undefined>,
    read: () => Promise<T>,
  ): Promise<T> => {
    const before = { ...process.env };
    try {
      Object.assign(process.env, changes);
      for (const [name, value] of Object.entries(changes))
        if (value === undefined) delete process.env[name];
      return await read();
    } finally {
      process.env = before;
    }
  };

  it('carries the defaults .env.example writes down when nothing is set', async () => {
    await withEnvironment({ PORT: undefined, HOST: undefined }, async () => {
      const app = buildApp();
      try {
        await app.ready();

        expect(app.config.PORT).toBe(3000);
        expect(app.config.HOST).toBe('0.0.0.0');
      } finally {
        await app.close();
      }
    });
  });

  /**
   * The point of checking the environment at start-up rather than at the point of use: the process that
   * cannot work refuses to start, and says which variable is why.
   */
  it('refuses to start on a variable it cannot use, and names it', async () => {
    await withEnvironment({ PORT: 'the-usual-one' }, async () => {
      const app = buildApp();
      try {
        await expect(app.ready()).rejects.toThrow(/PORT/);
      } finally {
        await app.close();
      }
    });
  });
});

/**
 * What a browser is told to enforce, and who is allowed to ask this service for anything at all.
 *
 * Asserted through the framework rather than by reading the registration: the whole value of both plugins
 * is in the headers that come back, and a test that checks they were registered proves only that.
 */
describe('the edge a browser meets', () => {
  const withOrigins = async <T>(
    origins: string | undefined,
    use: (app: ReturnType<typeof buildApp>) => Promise<T>,
  ) => {
    const before = process.env.CORS_ALLOWED_ORIGINS;
    if (origins === undefined) delete process.env.CORS_ALLOWED_ORIGINS;
    else process.env.CORS_ALLOWED_ORIGINS = origins;
    const app = buildApp();
    try {
      await app.ready();
      return await use(app);
    } finally {
      await app.close();
      if (before === undefined) delete process.env.CORS_ALLOWED_ORIGINS;
      else process.env.CORS_ALLOWED_ORIGINS = before;
    }
  };

  it('sends the security headers on every response', async () => {
    const headers = await withOrigins(
      undefined,
      async (app) => (await app.inject({ method: 'GET', url: '/health' })).headers,
    );

    // `nosniff` is the one that matters most for a JSON API: without it a browser may decide a response
    // is HTML because of what is inside it, and run what it finds.
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBeDefined();
    expect(headers['content-security-policy']).toBeDefined();
  });

  it('answers a cross-origin request with nothing, until an origin is allowed', async () => {
    // Empty is the default, and it is same-origin only: the response carries no permission at all, so
    // the browser refuses to hand it to the page that asked.
    const headers = await withOrigins(
      '',
      async (app) =>
        (
          await app.inject({
            method: 'GET',
            url: '/health',
            headers: { origin: 'http://evil.example' },
          })
        ).headers,
    );

    expect(headers['access-control-allow-origin']).toBeUndefined();
  });

  it('permits exactly the origins it was given, and no others', async () => {
    const allowed = await withOrigins(
      'http://localhost:5173',
      async (app) =>
        (
          await app.inject({
            method: 'GET',
            url: '/health',
            headers: { origin: 'http://localhost:5173' },
          })
        ).headers,
    );
    const refused = await withOrigins(
      'http://localhost:5173',
      async (app) =>
        (
          await app.inject({
            method: 'GET',
            url: '/health',
            headers: { origin: 'http://localhost:5174' },
          })
        ).headers,
    );

    expect(allowed['access-control-allow-origin']).toBe('http://localhost:5173');
    // A near miss is a miss: one port out is a different origin, and nothing here guesses.
    expect(refused['access-control-allow-origin']).toBeUndefined();
  });

  it('reads an allow-list the way a deployment writes one', () => {
    expect(allowedOrigins('http://a.example, http://b.example')).toEqual([
      'http://a.example',
      'http://b.example',
    ]);
    // A trailing comma must not become a permission for the empty string, which is what an `origin`
    // header carries when a request has none.
    expect(allowedOrigins('http://a.example,')).toEqual(['http://a.example']);
    expect(allowedOrigins('')).toEqual([]);
  });
});
