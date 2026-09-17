import { afterEach, describe, expect, it } from 'vitest';

import {
  fixedSource,
  flagEnabled,
  flagVariable,
  loadFlags,
  noFlags,
  setFlagSource,
} from '../src/flags';

// `setFlagSource` sets module state, which is the point of it — so a test that sets one puts it back.
afterEach(() => {
  setFlagSource(noFlags);
});

describe('flagVariable', () => {
  it('spells a flag the way Vite inlines it', () => {
    expect(flagVariable('checkout-v2')).toBe('VITE_FLAG_CHECKOUT_V2');
    expect(flagVariable('publish-table')).toBe('VITE_FLAG_PUBLISH_TABLE');
  });
});

describe('loadFlags', () => {
  it('reads the flags this bundle was built with, by key', async () => {
    const source = await loadFlags({
      VITE_FLAG_CHECKOUT_V2: 'on',
      VITE_USERS_ISSUER: 'https://issuer',
    });

    expect(source.value('checkout-v2')).toBe('on');
    // Everything in the bundle's environment is not a flag.
    expect(source.snapshot()).toEqual({ 'checkout-v2': 'on' });
  });

  it('is every flag off when the bundle was built with none', async () => {
    expect((await loadFlags({})).snapshot()).toEqual({});
  });
});

describe('flagEnabled', () => {
  it('is on only for the exact value `on`', () => {
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'on' }))).toBe(true);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'off' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({ 'checkout-v2': 'true' }))).toBe(false);
    expect(flagEnabled('checkout-v2', fixedSource({}))).toBe(false);
  });

  it('is off before this bundle has been told anything', () => {
    expect(flagEnabled('checkout-v2')).toBe(false);
  });

  it('reads what the bundle was given once it has been handed a source', () => {
    setFlagSource(fixedSource({ 'checkout-v2': 'on' }));

    expect(flagEnabled('checkout-v2')).toBe(true);
  });
});
