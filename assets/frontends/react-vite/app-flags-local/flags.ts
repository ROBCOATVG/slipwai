/**
 * Whether a feature flag is on — in this bundle, which is the only place this project has to ask.
 *
 * This project has nowhere to deploy (`--target none`), so there is no environment holding a flag and no
 * service to ask for one: the value comes from the bundle, and the bundle is built from the repository's
 * `.env` (documented by `.env.example` at the root; `vite.config.ts` points Vite at that directory).
 *
 * ── One flag, one name ────────────────────────────────────────────────────────────────────────────────
 * `checkout-v2` is read as `VITE_FLAG_CHECKOUT_V2` — upper-cased, dashes to underscores. `flagVariable` is
 * that transform, written here and nowhere else, because a hand-derived variable name is a typo waiting to
 * happen and a typo reads as *absent*, which reads as *off*: the feature never turns on and the flip
 * merely looks broken. Vite copies only `VITE_`-prefixed keys into the bundle, which is why the flag
 * carries the prefix and why nothing without one can leak in by accident.
 *
 * ── The same shape a deployed project has ─────────────────────────────────────────────────────────────
 * A project with somewhere to deploy reads this file's counterpart, which asks its service over
 * `GET /api/flags` instead — because there a flag lives in the environment and the service is the one
 * enforcing it. The two export the same things, so `main.tsx` is identical in both and a slice always
 * writes `flagEnabled('checkout-v2')`. Only where the value comes from differs, which is the whole of
 * what having somewhere to deploy changes.
 *
 * ── Off is the answer to every question this cannot answer ────────────────────────────────────────────
 * `flagEnabled` is `true` only for the exact value `'on'`. `'off'`, a typo, nothing at all: all off. That
 * is the direction that hides a feature rather than half-revealing one.
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

/** The environment variable a flag's key is read from here: `checkout-v2` → `VITE_FLAG_CHECKOUT_V2`. */
export function flagVariable(key: string): string {
  return `VITE_FLAG_${key.toUpperCase().replace(/-/g, '_')}`;
}

/**
 * The flags this bundle was built with.
 *
 * Async and awaited by `main.tsx` only so that this file and its deployed counterpart have one shape;
 * there is nothing to wait for here, because `import.meta.env` carries the values Vite already inlined.
 *
 * @param environment where to read from: this bundle's own by default, a plain object in a test
 */
export async function loadFlags(
  environment: Record<string, string | undefined> = import.meta.env,
): Promise<FlagSource> {
  const flags: Record<string, string> = {};
  for (const [variable, value] of Object.entries(environment)) {
    if (variable.startsWith('VITE_FLAG_') && typeof value === 'string') {
      flags[variable.slice('VITE_FLAG_'.length).toLowerCase().replace(/_/g, '-')] = value;
    }
  }
  return fixedSource(flags);
}

/**
 * `true` only for the exact value `'on'`. Anything else — `'off'`, a typo, nothing at all — is off.
 *
 * @param key the flag's name in one spelling
 * @param source where to read it from: what this bundle was given by default, `fixedSource` in a test
 */
export function flagEnabled(key: string, source: FlagSource = current): boolean {
  return source.value(key) === 'on';
}
