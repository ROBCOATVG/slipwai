import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// backing-service:__TRANSPORT__:begin
/**
 * Where `/api` goes while you are developing.
 *
 * The app fetches relative paths — `/api/...` — in every environment, and the dev server forwards them to
 * the service. That is not a convenience: a browser calling a *different* origin than the one it was
 * served from turns every request into a CORS preflight and forces the service to publish which origins it
 * trusts, configuration that exists only because of how the dev server happened to be wired. Proxying here
 * means production can serve both from one origin with no code change, and the frontend never holds an
 * absolute backend URL for somebody to forget to change.
 *
 * API_ORIGIN is read from the environment because the address depends on how the service was started:
 * `http://localhost:3000` when it runs beside you (`make dev`), and `http://service:3000` inside the
 * Compose network (`make demo`), where `localhost` is the web container itself.
 */
const apiOrigin = process.env.API_ORIGIN ?? 'http://localhost:3000';

// backing-service:__TRANSPORT__:end
export default defineConfig({
  plugins: [react()],
  // Where Vite looks for `.env` files. Its default is this directory, but the app's settings live two
  // levels up: the repository has one `.env`, documented by `.env.example` at the root, holding every
  // part's configuration, and the browser app reads that file rather than keeping a second one here.
  // Vite copies only the keys prefixed `VITE_` into the bundle — everything else in the file, secrets
  // included, stays out — which is why every value this app reads carries the prefix: a feature flag as
  // `VITE_FLAG_<KEY>`, a login as `VITE_USERS_*`. Not tied to any one of them, deliberately: a flag has
  // nothing to do with who signs in, and an app whose env file moved with the identity answer would read
  // nothing at all with `--users none`. `import.meta.dirname` is this file's directory, resolved by Vite
  // when it loads the config, so the path holds wherever the build is started from.
  envDir: `${import.meta.dirname}/../..`,
  server: {
    // Pinned, and a clash is an error rather than a silent move to 5174. A demo has to be able to state
    // the address it will be at before it starts, and every printed URL is wrong the moment Vite picks a
    // different port on its own.
    port: 5173,
    strictPort: true,
    // Vite binds localhost by default, deliberately — a dev server is not something to put on the LAN.
    // Inside a container localhost is the container, so `make demo` sets WEB_HOST and nothing else does.
    host: process.env.WEB_HOST ?? 'localhost',
    // backing-service:__TRANSPORT__:begin
    proxy: {
      // Forwarded with the prefix intact and nothing rewritten, so `/api/orders` is that path on both
      // sides. The alternative — stripping `/api` here — buys a shorter route in the service and costs a
      // rule that exists only in this file: production would have to strip the same prefix in an ingress
      // for the app to keep working, and nothing would notice until it did not.
      //
      // So `/api` is the service's product surface. `/health` sits outside it on purpose: it is a probe
      // for whatever runs the process, not something a browser calls.
      //
      // `changeOrigin` rewrites the forwarded Host header to the target's. Without it the service sees
      // `localhost:5173`, so anything it builds from the request — a redirect, a Location header, an
      // absolute link in a payload — points back at the dev server instead of at itself.
      '/api': { target: apiOrigin, changeOrigin: true },
      // And the probe, which is not part of that surface — it is forwarded here and nowhere else because
      // a project with nowhere to deploy has no product route for the skeleton's one screen to call, and
      // showing "the service could not be reached" on a working machine teaches the wrong thing. A
      // deployed environment routes `/api` and not this, which is why a project *with* a target has its
      // screen call `/api/flags` instead and needs no rule here.
      '/health': { target: apiOrigin, changeOrigin: true },
    },
    // backing-service:__TRANSPORT__:end
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
});
