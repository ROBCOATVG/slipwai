/**
 * Whether a feature flag is on — in this bundle, asked of the service that enforces it.
 *
 * One product flag has one name and one value on both sides of `/api`. The service reads it from its own
 * environment; this app asks the service, over `GET /api/flags`, and the two move together.
 *
 * ── Why this is a fetch and not a build-time value ────────────────────────────────────────────────────
 * Vite inlines a `VITE_`-prefixed value while it *builds*, so a flag compiled into a bundle is a property
 * of that build and not of the environment the bundle runs in. That used to be how this file worked, and
 * it gave one flag two clocks: the service's moved in a restart, the browser's only when the environment
 * was deployed again and its bundle rebuilt. Every screen gated on a flag then had an ordering rule
 * attached to it — turn it on in the service first, off in the bundle first — and the rule existed only
 * because of how the value arrived.
 *
 * Asking the service removes the second clock. There is one source of truth, it is the service that
 * enforces the flag anyway, and nothing is inlined into this bundle at all — which is also why a rollback
 * no longer restores a bundle carrying stale flag values.
 *
 * Nothing new is exposed by this: the keys and their values were already sitting in the shipped
 * JavaScript when they were inlined.
 *
 * ── Off is the answer to every question this cannot answer ────────────────────────────────────────────
 * `flagEnabled` is `true` only for the exact value `'on'`, the spelling the service answers with. A key
 * nothing set, a value this does not understand, a request that failed, a service that has not been asked
 * yet: all off. That is the direction that hides a feature rather than half-revealing one — a screen
 * inviting a customer to do something the API will refuse.
 *
 * Failing closed is what makes the fetch safe to lose. `loadFlags` never rejects; a service that answers
 * badly leaves every flag off, and the app renders as it does with nothing released.
 *
 * ── The source is set once, at boot ───────────────────────────────────────────────────────────────────
 * `main.tsx` awaits `loadFlags()` and calls `setFlagSource` before it renders, so no screen paints with
 * flags it is about to change its mind about. Until then — and forever, in a test that does not set one —
 * the source is empty and every flag is off.
 *
 * Module state rather than a React context, deliberately. A context would mean a slice asked for a flag
 * through a hook, and `flagEnabled('checkout-v2')` is the one call shape the whole mechanism is built on:
 * `make check-flags` matches it to know a key is read, and `commands/drive.md` tells a slice to write it.
 * One bundle boots once, so the honest cost of the alternative is a second way to ask.
 */

/** Where this bundle's flags come from: a key in its one spelling, answered with the raw value or not. */
export interface FlagSource {
  value(key: string): string | undefined;
  snapshot(): Record<string, string>;
}

/** Flags held by key — what `loadFlags` builds, and what a test drives both paths with. */
export function fixedSource(values: Record<string, string | undefined>): FlagSource {
  return {
    value: (key) => values[key],
    snapshot: () =>
      Object.fromEntries(
        Object.entries(values).filter((entry): entry is [string, string] => entry[1] !== undefined),
      ),
  };
}

/** Every flag off, which is what this bundle answers before it has been told otherwise. */
export const noFlags: FlagSource = fixedSource({});

let current: FlagSource = noFlags;

/** Hand this bundle the flags it was given. Called once, from `main.tsx`, before the first render. */
export function setFlagSource(source: FlagSource): void {
  current = source;
}

/**
 * Ask the service what this environment's flags are set to. Never rejects: every failure is no flags.
 *
 * `/api/flags` relatively, so it is this origin in every environment — the dev server proxies `/api` and
 * CloudFront routes `/api/*` to the service, both with the prefix intact.
 *
 * @param fetcher the `fetch` to use; a test passes its own
 */
export async function loadFlags(fetcher: typeof fetch = fetch): Promise<FlagSource> {
  try {
    const response = await fetcher('/api/flags', { headers: { accept: 'application/json' } });
    if (!response.ok) {
      return noFlags;
    }
    const body: unknown = await response.json();
    if (typeof body !== 'object' || body === null || Array.isArray(body)) {
      return noFlags;
    }
    const flags: Record<string, string> = {};
    for (const [key, value] of Object.entries(body)) {
      if (typeof value === 'string') {
        flags[key] = value;
      }
    }
    return fixedSource(flags);
  } catch {
    // A network failure, an abort, a body that is not JSON. Off is the safe answer to all of them.
    return noFlags;
  }
}

/**
 * `true` only for the exact value `'on'`. Anything else — `'off'`, a typo, nothing at all — is off.
 *
 * @param key the flag's name as `infra/service/flags.auto.tfvars` declares it, in one spelling
 * @param source where to read it from: what this bundle was given by default, `fixedSource` in a test
 */
export function flagEnabled(key: string, source: FlagSource = current): boolean {
  return source.value(key) === 'on';
}
