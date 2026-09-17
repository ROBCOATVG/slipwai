import { afterEach, describe, expect, it } from 'vitest';

import { fixedSource, flagEnabled, loadFlags, noFlags, setFlagSource } from '../src/flags';

// `setFlagSource` sets module state, which is the point of it — so a test that sets one puts it back,
// rather than leaving the next test reading flags it never asked for.
afterEach(() => {
  setFlagSource(noFlags);
});

/** A `fetch` that answers with this body and status, and records nothing else. */
function answering(body: unknown, status = 200): typeof fetch {
  return (async () =>
    new Response(typeof body === 'string' ? body : JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    })) as unknown as typeof fetch;
}

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

describe('loadFlags', () => {
  it('reads what the service says this environment is set to', async () => {
    const source = await loadFlags(answering({ 'checkout-v2': 'on', 'publish-table': 'off' }));

    expect(source.value('checkout-v2')).toBe('on');
    expect(source.value('publish-table')).toBe('off');
  });

  it('is every flag off when the service refuses', async () => {
    // Failing closed is what makes the request safe to lose: the app renders as it does with nothing
    // released, rather than showing a screen the API will refuse.
    const source = await loadFlags(answering({ error: 'nope' }, 503));

    expect(source.snapshot()).toEqual({});
  });

  it('is every flag off when the request fails outright', async () => {
    const throwing = (async () => {
      throw new Error('network');
    }) as unknown as typeof fetch;

    const source = await loadFlags(throwing);

    expect(source.snapshot()).toEqual({});
  });

  it('is every flag off when the body is not an object of flags', async () => {
    // A proxy answering HTML, a misconfigured route, an array where an object was meant. None of them is
    // a flag, and guessing at one is how a bundle turns a broken deploy into a released feature.
    expect((await loadFlags(answering('<!doctype html>'))).snapshot()).toEqual({});
    expect((await loadFlags(answering(['checkout-v2']))).snapshot()).toEqual({});
    expect((await loadFlags(answering(null))).snapshot()).toEqual({});
  });

  it('keeps only the values that are strings', async () => {
    const source = await loadFlags(answering({ 'checkout-v2': 'on', 'publish-table': true }));

    expect(source.snapshot()).toEqual({ 'checkout-v2': 'on' });
  });
});

describe('flagEnabled', () => {
  it('is on only for the value the service answers with', () => {
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'on' }))).toBe(true);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'off' }))).toBe(false);
  });

  it('is off for a value it does not understand, and for one nothing set', () => {
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'true' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'ON' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({}))).toBe(false);
  });

  it('is off before this bundle has been told anything', () => {
    // What every screen answers between load and `main.tsx` handing over the flags — and forever, in a
    // project whose service has none to give.
    expect(flagEnabled('checkout-v2')).toBe(false);
  });

  it('reads what the bundle was given once it has been handed a source', () => {
    setFlagSource(fixedSource({ 'checkout-v2': 'on' }));

    expect(flagEnabled('checkout-v2')).toBe(true);
  });
});
