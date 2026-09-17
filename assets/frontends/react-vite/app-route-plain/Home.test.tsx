import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HomeView } from '../../src/routes/Home';

/**
 * A hand-written `fetch`, answering whatever the case is about.
 *
 * No mocking framework anywhere in this repository. `HomeView` takes the fetch as a prop precisely so a
 * test can describe one answer as a plain function — and a fake that implements the contract survives a
 * refactoring that a recorded call sequence would not. The `finding-seams` and `testing` skills say why.
 */
function answering(body: unknown, status = 200): typeof fetch {
  return (async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    })) as unknown as typeof fetch;
}

describe('HomeView', () => {
  it('says it is asking before the service has answered', () => {
    render(<HomeView fetcher={(() => new Promise(() => {})) as unknown as typeof fetch} />);

    expect(screen.getByRole('status')).toHaveTextContent('Asking the service');
  });

  it('shows what the service answered', async () => {
    render(<HomeView fetcher={answering({ status: 'ok' })} />);

    expect(await screen.findByText(/"status":"ok"/)).toBeVisible();
  });

  it('says so, rather than nothing, when the service refuses', async () => {
    render(<HomeView fetcher={answering({ error: 'nope' }, 503)} />);

    expect(await screen.findByText(/answered 503/)).toBeVisible();
  });

  it('says so, rather than nothing, when the service cannot be reached', async () => {
    // The failing case is the one worth a test: a skeleton that renders an empty panel when its own API
    // is down is a skeleton that teaches nobody anything on the day it matters.
    const unreachable = (async () => {
      throw new Error('network');
    }) as unknown as typeof fetch;

    render(<HomeView fetcher={unreachable} />);

    expect(await screen.findByText(/could not be reached/)).toBeVisible();
  });
});
