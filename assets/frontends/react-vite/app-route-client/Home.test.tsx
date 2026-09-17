import type { ApiClient } from '__API_CLIENT__';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HomeView } from '../../src/routes/Home';

/**
 * A hand-written stand-in for the typed client, answering whatever the case is about.
 *
 * No mocking framework anywhere in this repository. `HomeView` takes the client as a prop precisely so a
 * test can describe one answer as a plain object — and a fake that implements the contract survives a
 * refactoring that a recorded call sequence would not. The `finding-seams` and `testing` skills say why.
 */
function answering(body: unknown): ApiClient {
  return { get: async () => body as never };
}

/** A client for a service nothing can reach, which is what the client throws for. */
function unreachable(message: string): ApiClient {
  return {
    get: async () => {
      throw new Error(message);
    },
  };
}

describe('HomeView', () => {
  it('says it is asking before the service has answered', () => {
    render(<HomeView client={{ get: () => new Promise(() => {}) }} />);

    expect(screen.getByRole('status')).toHaveTextContent('Asking the service');
  });

  it('shows what the service answered', async () => {
    render(<HomeView client={answering({ status: 'ok' })} />);

    expect(await screen.findByText(/"status":"ok"/)).toBeVisible();
  });

  it('says so, rather than nothing, when the service cannot be reached', async () => {
    // The failing case is the one worth a test: a skeleton that renders an empty panel when its own API
    // is down is a skeleton that teaches nobody anything on the day it matters.
    render(<HomeView client={unreachable('/health could not be reached')} />);

    expect(await screen.findByText(/could not be reached/)).toBeVisible();
  });
});
