import { describe, expect, it } from 'vitest';

import {
  appConfigSource,
  defaultSource,
  environmentSource,
  fixedSource,
  flagEnabled,
  flagKey,
  flagVariable,
} from '../src/flags.js';

describe('flagVariable', () => {
  it('spells a flag the way the stack asks ECS to spell it', () => {
    // The same transform as `FLAG_${upper(replace(flag.key, "-", "_"))}` in infra/service/flags.tf, which
    // is what puts the value in this container's environment at start-up. If this expectation changes the
    // flag stops arriving — and an absent flag reads as off, so nothing fails loudly to say so.
    expect(flagVariable('checkout-v2')).toBe('FLAG_CHECKOUT_V2');
    expect(flagVariable('publish-table')).toBe('FLAG_PUBLISH_TABLE');
  });
});

describe('flagKey', () => {
  it('is the exact inverse of the transform, for every key a project may declare', () => {
    // Exact only because `check-flags.py` holds a key to `[a-z0-9][a-z0-9-]*`: no underscore can be in a
    // key, so every underscore in the variable came from a dash.
    for (const key of ['checkout-v2', 'publish-table', 'a', 'b2b-invoicing-v10']) {
      expect(flagKey(flagVariable(key))).toBe(key);
    }
  });

  it('does not answer for a variable that is not a flag', () => {
    expect(flagKey('DATABASE_URL')).toBeUndefined();
    expect(flagKey('PGSSLMODE')).toBeUndefined();
    // The browser's spelling of the same flag. It is a flag, but it is not this side's — the prefix
    // anchor is what keeps the two apart, here and in `check-flags.py`'s read pattern.
    expect(flagKey('VITE_FLAG_CHECKOUT_V2')).toBeUndefined();
  });
});

describe('environmentSource', () => {
  it('reads a key under the variable name the stack gives it', () => {
    // The transform is the environment's business and nobody else's: this is the only source that knows
    // a flag is carried under a different name than the one it is declared with.
    expect(environmentSource({ FLAG_CHECKOUT_V2: 'on' }).value('checkout-v2')).toBe('on');
  });

  it('answers nothing for a variable the environment does not carry', () => {
    expect(environmentSource({}).value('checkout-v2')).toBeUndefined();
  });

  it('snapshots every flag it carries by key, and nothing that is not one', () => {
    // What the service serves to the browser app, which cannot read these itself. The database URL is in
    // the same environment and is not a flag; `VITE_FLAG_…` is a flag and is not this side's.
    const source = environmentSource({
      FLAG_CHECKOUT_V2: 'on',
      FLAG_PUBLISH_TABLE: 'off',
      DATABASE_URL: 'postgres://nope',
      VITE_FLAG_CHECKOUT_V2: 'on',
    });
    expect(source.snapshot()).toEqual({ 'checkout-v2': 'on', 'publish-table': 'off' });
  });

  it('leaves an unset variable out of the snapshot rather than reporting it as empty', () => {
    // Absent is off, and saying so by omission is the same answer `value` gives.
    expect(environmentSource({ FLAG_CHECKOUT_V2: undefined }).snapshot()).toEqual({});
  });
});

describe('fixedSource', () => {
  it('is keyed by the flag key, so a test never spells a variable', () => {
    expect(fixedSource({ 'checkout-v2': 'on' }).value('checkout-v2')).toBe('on');
    expect(fixedSource({}).value('checkout-v2')).toBeUndefined();
  });

  it('snapshots what it was given, without the keys nothing set', () => {
    expect(fixedSource({ 'checkout-v2': 'on', 'publish-table': undefined }).snapshot()).toEqual({
      'checkout-v2': 'on',
    });
  });
});

describe('appConfigSource', () => {
  it('is every flag off until the agent has answered', () => {
    // Built and asked immediately: the first refresh has not landed, and off is what a flag reads while
    // this cannot answer — the same direction the rest of this file takes.
    const source = appConfigSource({}, 3_600_000);

    expect(source.value('checkout-v2')).toBeUndefined();
    expect(source.snapshot()).toEqual({});
  });
});

describe('defaultSource', () => {
  it('reads the environment unless the stack says otherwise', () => {
    // `FLAG_TRANSPORT` is set by infra/service/flags.tf and read here and in no other file, so no slice
    // ever learns which transport its environment runs.
    expect(defaultSource({ FLAG_CHECKOUT_V2: 'on' }).value('checkout-v2')).toBe('on');
    expect(
      defaultSource({ FLAG_TRANSPORT: 'ssm', FLAG_CHECKOUT_V2: 'on' }).value('checkout-v2'),
    ).toBe('on');
  });

  it('is the same AppConfig source every time, because that one owns a timer', () => {
    // `flagEnabled` resolves this default on every read, so a fresh source per read would start a polling
    // timer per flag lookup.
    const environment = { FLAG_TRANSPORT: 'appconfig' };

    expect(defaultSource(environment)).toBe(defaultSource(environment));
  });
});

describe('flagEnabled', () => {
  it('is on only for the value `make flag` writes', () => {
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'on' }))).toBe(true);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'off' }))).toBe(false);
  });

  it('is off when nothing set it, rather than throwing', () => {
    // The window between merging code that reads a flag and the apply that creates its parameter. Off is
    // a feature nobody can see yet; throwing is a task that will not start.
    expect(flagEnabled('checkout-v2', fixedSource({}))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': undefined }))).toBe(false);
  });

  it('is off for a value it does not understand', () => {
    // What a shell, a tfvars file or a hand-run `aws ssm put-parameter` would let somebody write. None of
    // them is the spelling, so all of them are off: a flag whose value is not understood hides the feature
    // it gates rather than half-revealing one.
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'true' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': '1' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'ON' }))).toBe(false);
  });

  it('reads through whichever source it is given, environment included', () => {
    // The two implementations meeting at one call: same key, same answer, different transport.
    expect(flagEnabled('checkout-v2', environmentSource({ FLAG_CHECKOUT_V2: 'on' }))).toBe(true);
    expect(flagEnabled('checkout-v2', environmentSource({}))).toBe(false);
  });
});
