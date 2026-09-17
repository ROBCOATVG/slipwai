import { defineConfig } from 'vitest/config';

/**
 * The db-backed suite, kept out of the default config so `make verify` needs no Docker. `make
 * test-integration` is the only thing that runs this.
 *
 * Sequential on purpose: every spec here shares one database, and the concurrency test asserts on how
 * many of *its own* simultaneous appends won. Parallel files racing through the same table would make
 * that assertion depend on unrelated tests.
 */
export default defineConfig({
  test: {
    include: ['tests/integration/**/*.test.ts'],
    fileParallelism: false,
  },
});
