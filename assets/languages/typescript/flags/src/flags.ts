/**
 * Whether a feature flag is on — the service's half of a flag, and the only place this side reads one.
 *
 * A flag is what makes merging and releasing two decisions. Every commit that passes `verify` on `main`
 * reaches production, so work that is not finished has to arrive there dark: the branch is merged, the
 * flag is off, and nobody outside sees it until somebody flips it. `.specify/memory/constitution.md`
 * requires exactly that, and this file is where the requirement stops being prose.
 *
 * ── One flag, one name ────────────────────────────────────────────────────────────────────────────────
 * A flag is declared once, in `infra/service/flags.auto.tfvars`, under the service that reads it, with a
 * key in one spelling: `checkout-v2`. Ask by key and the declaration and the code cannot drift apart —
 * which is the whole reason a slice calls `flagEnabled('checkout-v2')` and never reaches for a variable
 * name of its own. A hand-derived variable is a typo waiting to happen, and a typo reads as *absent*,
 * which reads as *off*: the feature never turns on and the flip merely looks broken.
 *
 * ── Where a value comes from is one object, and it is not this function ───────────────────────────────
 * A `FlagSource` answers two questions and no others: what this environment holds for one key, and what
 * it holds for all of them. Today there is one implementation and `defaultSource` returns it: the stack
 * turns each key into an SSM parameter and has ECS resolve it into this container's environment as
 * `FLAG_CHECKOUT_V2` — upper-cased, dashes to underscores — so `environmentSource` applies that transform
 * and reads `process.env`. `flagVariable` is the transform and `flagKey` is its inverse, both written
 * here and nowhere else, and both pinned by a test against the HCL that has to agree with them.
 *
 * The point of the seam is that it is keyed by the flag's own key rather than by a variable name. A
 * transport that is not an environment — an AppConfig agent beside this container, answered over
 * loopback, which is what a flag that has to move *without* a restart needs — is then a second
 * `FlagSource` and a one-line change to `defaultSource`, not a change to any call site, any test, or the
 * rule in `AGENTS.md` that points at this file. `docs/deployment.md` says which of the two this project
 * has and what a flip therefore costs.
 *
 * `snapshot` is the second question because something has to answer it: the flags this service holds are
 * served to the browser app, which cannot read them itself. It is deliberately a *snapshot* and not a
 * subscription — the values as of the moment it was asked, which is all a transport polling an agent can
 * honestly promise.
 *
 * ── Off is the answer to every question this cannot answer ────────────────────────────────────────────
 * `flagEnabled` is `true` only for the exact string `'on'` — the spelling `make flag` writes and the only
 * one `flags.auto.tfvars` seeds. `'off'`, `'true'`, `'1'`, a value that never arrived: all off. That is
 * the safe direction, and it matters most in the window between merging code that reads a flag and the
 * apply that creates its parameter. In that window this returns `false` rather than throwing, so a task
 * starts with the feature quietly off instead of crash-looping.
 *
 * ── The seam exists so both paths can be tested ───────────────────────────────────────────────────────
 * A test drives either path by passing a source, which is the whole reason the value is not read at the
 * point of use: `fixedSource({ 'checkout-v2': 'on' })` for the on path and `fixedSource({})` for the one
 * production is running while the flag is off. It is keyed by key, so a test never has to know how this
 * environment happens to carry a flag. `make check-flags` holds every declared flag to having both paths
 * covered, because while a flag is off the branch running in production is the one the slice's own tests
 * do not reach — and "it worked before the branch was added" is not evidence about the code after it.
 * `process.env` is read here and in no other file.
 *
 * Locally there is no parameter store and no flip: the flag is whatever this process's environment says,
 * so `FLAG_CHECKOUT_V2=on make dev` is the whole of it.
 */

/** A process environment, or the plain object standing in for one. */
export type FlagEnvironment = Record<string, string | undefined>;

/**
 * Where this service's flags come from.
 *
 * Keyed by the flag's key and not by an environment variable, so that a transport which is not an
 * environment is an implementation of this and nothing more.
 */
export interface FlagSource {
  /** This environment's raw value for one flag, or nothing when it carries none. */
  value(key: string): string | undefined;

  /**
   * Every flag this source carries, by key, as of now.
   *
   * A snapshot rather than a subscription: a transport that polls an agent can promise the values it last
   * saw and nothing stronger. Only flags with a value appear — an absent flag is off, and saying so by
   * omission is the same answer `value` gives.
   */
  snapshot(): Record<string, string>;
}

/** The prefix the stack gives every flag variable, and the one `flagKey` will answer to. */
const PREFIX = 'FLAG_';

/** The environment variable a flag's key is read from: `checkout-v2` → `FLAG_CHECKOUT_V2`. */
export function flagVariable(key: string): string {
  return `${PREFIX}${key.toUpperCase().replace(/-/g, '_')}`;
}

/**
 * The key a flag variable came from: `FLAG_CHECKOUT_V2` → `checkout-v2`, and nothing for a variable that
 * is not a flag's.
 *
 * The inverse is exact only because a key may not contain an underscore — `check-flags.py` holds every
 * declared key to `[a-z0-9][a-z0-9-]*` — so every underscore in the variable came from a dash. It is
 * deliberately anchored on the prefix, which is why `VITE_FLAG_CHECKOUT_V2`, the browser's spelling of
 * the same flag, is not a flag variable here.
 */
export function flagKey(variable: string): string | undefined {
  if (!variable.startsWith(PREFIX)) {
    return undefined;
  }
  return variable.slice(PREFIX.length).toLowerCase().replace(/_/g, '-');
}

/** Flags carried by an environment, under the variable names `infra/service/flags.tf` gives them. */
export function environmentSource(environment: FlagEnvironment = process.env): FlagSource {
  return {
    value: (key) => environment[flagVariable(key)],
    snapshot: () => {
      const flags: Record<string, string> = {};
      for (const [variable, value] of Object.entries(environment)) {
        const key = flagKey(variable);
        if (key !== undefined && value !== undefined) {
          flags[key] = value;
        }
      }
      return flags;
    },
  };
}

/**
 * Flags held by key, which is what a test drives both paths with and what a document-shaped transport
 * hands back. A key the object does not carry is off, exactly as an unset variable is.
 */
export function fixedSource(values: Record<string, string | undefined>): FlagSource {
  return {
    value: (key) => values[key],
    snapshot: () =>
      Object.fromEntries(
        Object.entries(values).filter((entry): entry is [string, string] => entry[1] !== undefined),
      ),
  };
}

/**
 * The AppConfig agent beside this container, answered over loopback.
 *
 * What `flag_transport = "appconfig"` buys: a flip takes effect without a restart. The agent polls
 * AppConfig with the task role's permissions and serves the last configuration it saw on `localhost:2772`,
 * so this makes a plain HTTP call and no image in this project carries an AWS SDK — the sidecar holds it.
 *
 * ── Why this holds a snapshot rather than asking per read ─────────────────────────────────────────────
 * `flagEnabled` is synchronous and must stay so: every call site in every slice depends on it, and an
 * `await` at the point a branch is taken would change all of them. `fetch` is not synchronous, so the
 * value has to be here before it is asked for. This keeps the last configuration it fetched and refreshes
 * it on an interval; `value` reads that.
 *
 * The honest consequence is that "no restart" does not mean "instantly": a flip is visible within
 * `refreshMilliseconds`, on top of whatever the agent's own poll adds. That is seconds rather than the two
 * minutes a rolling restart costs, which is the whole of what this transport is for.
 *
 * Empty until the first refresh lands, and empty again after a failure — so a flag is off while this
 * cannot answer, which is the same direction every other part of this file takes. `unref` keeps the timer
 * from holding the process open, so a task still exits when it is asked to.
 */
export function appConfigSource(
  environment: FlagEnvironment = process.env,
  refreshMilliseconds = 10_000,
): FlagSource {
  const application = environment.APPCONFIG_APPLICATION ?? '';
  const configured = environment.APPCONFIG_ENVIRONMENT ?? '';
  const profile = environment.APPCONFIG_PROFILE ?? '';
  const url =
    `http://localhost:2772/applications/${application}` +
    `/environments/${configured}/configurations/${profile}`;
  let flags: Record<string, string> = {};

  const refresh = async (): Promise<void> => {
    try {
      const response = await fetch(url, { headers: { accept: 'application/json' } });
      if (!response.ok) {
        flags = {};
        return;
      }
      const body: unknown = await response.json();
      if (typeof body !== 'object' || body === null || Array.isArray(body)) {
        flags = {};
        return;
      }
      flags = Object.fromEntries(
        Object.entries(body).filter(
          (entry): entry is [string, string] => typeof entry[1] === 'string',
        ),
      );
    } catch {
      // The agent not up yet, a body that is not JSON, the socket refused. Off answers all of them.
      flags = {};
    }
  };

  void refresh();
  setInterval(() => void refresh(), refreshMilliseconds).unref?.();

  return {
    value: (key) => flags[key],
    snapshot: () => ({ ...flags }),
  };
}

/**
 * Where this service's flags come from — the one line a change of transport is.
 *
 * `FLAG_TRANSPORT` is set by `infra/service/flags.tf` and read here and in no other file, so a slice never
 * learns which transport its environment runs. Anything but `appconfig` is the environment, which is what
 * makes the SSM shape the default everywhere and the only shape a project with no target can have.
 *
 * Called per read rather than resolved once at import, so that the transport is decided where it is used
 * rather than at module load. The AppConfig source is built **once** and kept: it owns a refresh timer, and
 * `flagEnabled` resolves this default on every read, so building a new one per read would start a timer per
 * flag lookup. The environment source holds nothing and is built freshly each time.
 */
let configured: FlagSource | undefined;

export function defaultSource(environment: FlagEnvironment = process.env): FlagSource {
  if (environment.FLAG_TRANSPORT !== 'appconfig') {
    return environmentSource(environment);
  }
  configured ??= appConfigSource(environment);
  return configured;
}

/**
 * `true` only for the exact value `'on'`. Anything else — `'off'`, a typo, nothing at all — is off.
 *
 * @param key the flag's name as `infra/service/flags.auto.tfvars` declares it, in one spelling
 * @param source where to read it from: this service's own by default, `fixedSource` in a test
 */
export function flagEnabled(key: string, source: FlagSource = defaultSource()): boolean {
  return source.value(key) === 'on';
}
