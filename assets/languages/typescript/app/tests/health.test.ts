import { describe, expect, it } from 'vitest';

import { health } from '../src/health.js';

describe('health', () => {
  it('reports ready', () => {
    expect(health()).toEqual({ status: 'ok' });
  });
});
